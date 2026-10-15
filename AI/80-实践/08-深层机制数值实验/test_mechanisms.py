"""运行：python -m unittest discover -s . -p 'test*.py' -v

断言比较独立公式、枚举或 PyTorch 自动微分；不使用 GPU，不启动 DDP 进程。
"""
from __future__ import annotations

import copy
import itertools
import math
import unittest
import torch
import torch.nn.functional as F
from torch import nn
from mechanisms import (
    projection, attention, attention_vjp, SiLUFunction, token_mean, ddp_local_objective,
    cached_causal_mask, rope, linear_attention_recurrent, compose_affine, dpo_loss,
    centered_advantage, speculative_masses, conformal_quantile, pass_at_k, ctc_collapse,
)

torch.set_num_threads(1)
DTYPE = torch.float64


class MechanismTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(731)

    def close(self, actual, expected, atol=1e-10, rtol=1e-9):
        actual = torch.as_tensor(actual)
        expected = torch.as_tensor(expected, dtype=actual.dtype, device=actual.device)
        torch.testing.assert_close(actual, expected, atol=atol, rtol=rtol)

    def test_01_projection_nonunit_and_zero(self):
        x = torch.tensor([2., 1.], dtype=DTYPE)
        u = torch.tensor([2., 0.], dtype=DTYPE)
        y = projection(x, u)
        self.close(y, [2., 0.])
        self.close(projection(y, u), y)
        self.close((x-y) @ u, 0.)
        with self.assertRaises(ValueError):
            projection(x, torch.zeros_like(u))

    def test_02_svd_tail_error(self):
        w = torch.diag(torch.tensor([5., 2., .1], dtype=DTYPE))
        u, s, vh = torch.linalg.svd(w)
        for rank, error in [(1, 4.01), (2, .01)]:
            approx = (u[:, :rank] * s[:rank]) @ vh[:rank]
            self.close((w-approx).square().sum(), error)

    def test_03_weighted_quantization_second_moment(self):
        x = torch.tensor([[10., 1.], [10., -1.]], dtype=DTYPE)
        moment = x.T @ x / len(x)
        for e, expected in [(torch.tensor([[.1, 0.]], dtype=DTYPE), 1.),
                            (torch.tensor([[0., .1]], dtype=DTYPE), .01)]:
            empirical = (x @ e.T).square().sum(-1).mean()
            self.close(empirical, torch.trace(e @ moment @ e.T))
            self.close(empirical, expected)
        # 非零均值时，中心化协方差会遗漏第一方向上的输出误差。
        centered = x-x.mean(0)
        self.assertNotEqual(moment[0, 0].item(), (centered.T@centered/len(x))[0, 0].item())

    def test_04_softmax_shift_and_cross_entropy_gradient(self):
        logits = torch.tensor([[1., -2., .5]], dtype=DTYPE, requires_grad=True)
        label = torch.tensor([2])
        loss = F.cross_entropy(logits, label)
        gradient, = torch.autograd.grad(loss, logits)
        expected = logits.softmax(-1).detach()
        expected[0, 2] -= 1
        self.close(gradient, expected)
        self.close(logits.softmax(-1), (logits+100).softmax(-1))

    def test_05_attention_vjp_against_autograd(self):
        q = torch.randn(3, 4, dtype=DTYPE, requires_grad=True)
        k = torch.randn(5, 4, dtype=DTYPE, requires_grad=True)
        v = torch.randn(5, 2, dtype=DTYPE, requires_grad=True)
        g = torch.randn(3, 2, dtype=DTYPE)
        out, _ = attention(q, k, v)
        reference = torch.autograd.grad(out, (q, k, v), g)
        actual = attention_vjp(q, k, v, g)
        for a, b in zip(actual[:3], reference):
            self.close(a, b)
        self.close(actual[3].sum(-1), torch.zeros(3, dtype=DTYPE))

    def test_06_attention_mask_and_finite_difference(self):
        q = torch.randn(2, 3, dtype=DTYPE, requires_grad=True)
        k = torch.randn(4, 3, dtype=DTYPE, requires_grad=True)
        v = torch.randn(4, 2, dtype=DTYPE, requires_grad=True)
        mask = torch.tensor([[True, True, False, False], [True, True, True, True]])
        g = torch.randn(2, 2, dtype=DTYPE)
        dq, dk, dv, ds = attention_vjp(q, k, v, g, mask)
        self.close(ds[~mask], torch.zeros_like(ds[~mask]))
        direction = torch.randn_like(q)
        epsilon = 1e-6
        plus = (attention(q+epsilon*direction, k, v, mask)[0]*g).sum()
        minus = (attention(q-epsilon*direction, k, v, mask)[0]*g).sum()
        self.close((plus-minus)/(2*epsilon), (dq*direction).sum(), atol=1e-8)
        with self.assertRaises(ValueError):
            attention(q, k, v, torch.zeros_like(mask))

    def test_07_softmax_competition_numbers(self):
        p = torch.tensor([.25, .75], dtype=DTYPE)
        dp = torch.tensor([2., 0.], dtype=DTYPE)
        self.close(p*(dp-(p*dp).sum()), [.375, -.375])

    def test_08_custom_silu_gradcheck_and_upstream(self):
        x = torch.randn(4, dtype=DTYPE, requires_grad=True)
        self.assertTrue(torch.autograd.gradcheck(SiLUFunction.apply, (x,)))
        self.assertTrue(torch.autograd.gradgradcheck(SiLUFunction.apply, (x,)))
        g = torch.tensor([2., -1., .5, 3.], dtype=DTYPE)
        actual, = torch.autograd.grad(SiLUFunction.apply(x), x, g)
        reference, = torch.autograd.grad(F.silu(x), x, g)
        self.close(actual, reference)

    def test_09_effective_token_weighting(self):
        actual = token_mean([torch.tensor(9., dtype=DTYPE), torch.tensor(9., dtype=DTYPE)], [9, 1])
        self.close(actual, 1.8)
        self.assertNotAlmostEqual(actual.item(), (1+9)/2)
        # 最后一个不足额窗口按真实计数，而非计划中的累积步数归一化。
        self.close(token_mean([torch.tensor(6., dtype=DTYPE)], [3]), 2.)

    def test_10_empty_window_skips_adamw_update(self):
        p = nn.Parameter(torch.tensor([1.], dtype=DTYPE))
        optimizer = torch.optim.AdamW([p], lr=.1, weight_decay=.2)
        before = p.detach().clone()
        objective = token_mean([p.sum()*0], [0])
        if objective is not None:
            objective.backward()
            optimizer.step()
        self.assertIsNone(objective)
        self.close(p, before)
        self.assertEqual(len(optimizer.state), 0)

    def test_11_ddp_simulated_unequal_rank_counts(self):
        # 仅模拟默认 all-reduce 后求平均的数学约定，没有创建进程组。
        x1 = torch.tensor([1., 1., 1., 1.], dtype=DTYPE)
        x2 = torch.tensor([3.], dtype=DTYPE)
        w = nn.Parameter(torch.tensor(2., dtype=DTYPE))
        rank_grads = []
        for data in (x1, x2):
            local_sum = (w*data).sum()
            gradient, = torch.autograd.grad(ddp_local_objective(local_sum, 5, 2), w)
            rank_grads.append(gradient)
        reference, = torch.autograd.grad((w*torch.cat((x1, x2))).mean(), w)
        self.close(torch.stack(rank_grads).mean(), reference)
        self.close(reference, 1.4)
        self.assertNotAlmostEqual(reference.item(), (x1.mean()+x2.mean()).item()/2)

    def test_12_ddp_simulated_zero_token_rank(self):
        w = nn.Parameter(torch.tensor(2., dtype=DTYPE))
        zero_grad, = torch.autograd.grad(ddp_local_objective(w*0, 2, 2), w)
        real_grad, = torch.autograd.grad(ddp_local_objective(3*w+5*w, 2, 2), w)
        self.close((zero_grad+real_grad)/2, 4.)

    def test_13_adamw_and_l2_are_not_same_preconditioning(self):
        w = torch.ones(2, dtype=DTYPE)
        gradient = torch.tensor([2., 2.], dtype=DTYPE)
        preconditioner = torch.tensor([1., 10.], dtype=DTYPE)
        lr, decay = .1, .2
        coupled = w-lr*preconditioner*(gradient+decay*w)
        decoupled = w-lr*preconditioner*gradient-lr*decay*w
        self.close(coupled[0], decoupled[0])
        self.assertNotAlmostEqual(coupled[1].item(), decoupled[1].item())

    def test_14_exact_cpu_resume_with_dropout_and_adam(self):
        def build():
            return nn.Sequential(nn.Linear(3, 5), nn.Dropout(.4), nn.Tanh(), nn.Linear(5, 1)).to(DTYPE)
        data = torch.randn(6, 3, dtype=DTYPE)
        target = torch.randn(6, 1, dtype=DTYPE)
        model = build()
        optimizer = torch.optim.Adam(model.parameters(), lr=.01)
        def step(m, opt):
            m.train(); opt.zero_grad(set_to_none=True)
            loss = F.mse_loss(m(data), target)
            loss.backward(); opt.step()
            return loss.detach().clone()
        step(model, optimizer)
        checkpoint = {'model': copy.deepcopy(model.state_dict()),
                      'optimizer': copy.deepcopy(optimizer.state_dict()),
                      'rng': torch.get_rng_state().clone()}
        expected_loss = step(model, optimizer)
        expected = copy.deepcopy(model.state_dict())
        restored = build()
        restored_optimizer = torch.optim.Adam(restored.parameters(), lr=.01)
        restored.load_state_dict(checkpoint['model'])
        restored_optimizer.load_state_dict(checkpoint['optimizer'])
        # 必须在模型初始化等消耗 RNG 的操作之后恢复 RNG。
        torch.set_rng_state(checkpoint['rng'])
        actual_loss = step(restored, restored_optimizer)
        self.assertTrue(torch.equal(expected_loss, actual_loss))
        for key, value in restored.state_dict().items():
            self.assertTrue(torch.equal(value, expected[key]), key)

    def test_15_convolution_adjoint_and_gradients(self):
        x = torch.tensor([[[1., 2., 3.]]], dtype=DTYPE, requires_grad=True)
        w = torch.tensor([[[1., -1.]]], dtype=DTYPE, requires_grad=True)
        g = torch.tensor([[[2., 3.]]], dtype=DTYPE)
        y = F.conv1d(x, w)
        dx, dw = torch.autograd.grad(y, (x, w), g)
        self.close(y.flatten(), [-1., -1.])
        self.close(dx.flatten(), [2., 1., -3.])
        self.close(dw.flatten(), [8., 13.])
        back = F.conv_transpose1d(g, w)
        self.close(back, dx)
        self.close((y*g).sum(), (x*back).sum())
        self.close((y*g).sum(), -5.)

    def test_16_transposed_convolution_is_not_inverse(self):
        kernel = torch.tensor([[[1., -1.]]], dtype=DTYPE)
        x = torch.tensor([[[1., 2., 3.]]], dtype=DTYPE)
        self.close(F.conv1d(x, kernel), F.conv1d(x+5, kernel))
        self.assertFalse(torch.allclose(F.conv_transpose1d(F.conv1d(x, kernel), kernel), x))

    def test_17_output_padding_resolves_shape_not_information(self):
        kernel = torch.ones(1, 1, 3, dtype=DTYPE)
        for original in (5, 6):
            y = F.conv1d(torch.ones(1, 1, original, dtype=DTYPE), kernel, stride=2, padding=1)
            self.assertEqual(y.shape[-1], 3)
        y = torch.ones(1, 1, 3, dtype=DTYPE)
        self.assertEqual(F.conv_transpose1d(y, kernel, stride=2, padding=1, output_padding=0).shape[-1], 5)
        self.assertEqual(F.conv_transpose1d(y, kernel, stride=2, padding=1, output_padding=1).shape[-1], 6)

    def test_18_aliasing_phase_counterexample(self):
        x = torch.tensor([1., -1.]*4, dtype=DTYPE)
        self.close(x[::2], torch.ones(4, dtype=DTYPE))
        self.close(x[1::2], -torch.ones(4, dtype=DTYPE))
        smooth = (x[:-1]+x[1:])/2
        self.close(smooth[::2], torch.zeros(4, dtype=DTYPE))

    def test_19_rope_fixed_content_global_shift(self):
        q = torch.randn(1, 4, dtype=DTYPE)
        k = torch.randn(1, 4, dtype=DTYPE)
        freq = torch.tensor([1., .1], dtype=DTYPE)
        def dot(m, n):
            return (rope(q, torch.tensor([m], dtype=DTYPE), freq)*rope(k, torch.tensor([n], dtype=DTYPE), freq)).sum()
        self.close(dot(3, 7), dot(103, 107))
        # 相对旋转的内积不是距离单调函数。
        self.assertGreater(math.cos(2*math.pi), math.cos(math.pi))

    def test_20_cached_mask_is_offset_aware(self):
        mask = cached_causal_mask(5, 2)
        self.assertEqual(tuple(mask.shape), (2, 7))
        self.assertEqual(mask[0].tolist(), [True]*6+[False])
        self.assertEqual(mask[1].tolist(), [True]*7)
        self.assertFalse(torch.equal(mask, torch.ones_like(mask).tril()))

    def test_21_cached_rope_attention_matches_full_pass(self):
        q, k, v = [torch.randn(7, 4, dtype=DTYPE) for _ in range(3)]
        positions = torch.arange(7, dtype=DTYPE)
        freq = torch.tensor([1., .1], dtype=DTYPE)
        qr, kr = rope(q, positions, freq), rope(k, positions, freq)
        full = attention(qr, kr, v, cached_causal_mask(0, 7))[0]
        # 缓存保存的是已旋转的 key，不再旋转第二次。
        cached_k = torch.cat((kr[:5], rope(k[5:], positions[5:], freq)))
        tail = attention(rope(q[5:], positions[5:], freq), cached_k, v, cached_causal_mask(5, 2))[0]
        self.close(tail, full[5:])
        sdpa = F.scaled_dot_product_attention(qr[5:][None, None], cached_k[None, None], v[None, None],
                                              attn_mask=cached_causal_mask(5, 2), dropout_p=0.)
        self.close(sdpa[0, 0], tail)

    def test_22_mla_absorption_under_declared_low_rank_model(self):
        c = torch.randn(2, 5, dtype=DTYPE)  # [latent_dim, token]
        wk = torch.randn(4, 2, dtype=DTYPE)
        wv = torch.randn(3, 2, dtype=DTYPE)
        q = torch.randn(4, dtype=DTYPE)
        direct_scores = q @ (wk @ c)
        latent_scores = (wk.T @ q) @ c
        self.close(direct_scores, latent_scores)
        weights = direct_scores.softmax(-1)
        self.close((wv @ c) @ weights, wv @ (c @ weights))

    def test_23_linear_attention_recurrent_matches_kernel_batch(self):
        q, k = [torch.rand(6, 3, dtype=DTYPE)+.1 for _ in range(2)]
        v = torch.randn(6, 2, dtype=DTYPE)
        result = linear_attention_recurrent(q, k, v)
        weights = q @ k.T
        weights = weights.masked_fill(~cached_causal_mask(0, 6), 0)
        reference = (weights/weights.sum(-1, keepdim=True)) @ v
        self.close(result, reference)

    def test_24_affine_scan_composition_associative(self):
        pairs = [(torch.randn(2, 2, dtype=DTYPE), torch.randn(2, dtype=DTYPE)) for _ in range(3)]
        a, b, c = pairs
        left = compose_affine(c, compose_affine(b, a))
        right = compose_affine(compose_affine(c, b), a)
        self.close(left[0], right[0]); self.close(left[1], right[1])

    def test_25_lora_zero_b_initialization_gradients(self):
        a = nn.Parameter(torch.randn(2, 3, dtype=DTYPE))
        b = nn.Parameter(torch.zeros(4, 2, dtype=DTYPE))
        x = torch.randn(3, dtype=DTYPE)
        g = torch.randn(4, dtype=DTYPE)
        ga, gb = torch.autograd.grad((b @ a @ x) @ g, (a, b))
        self.close(ga, torch.zeros_like(a))
        self.assertGreater(gb.norm().item(), 0.)
        a0 = nn.Parameter(torch.zeros_like(a)); b0 = nn.Parameter(torch.zeros_like(b))
        ga0, gb0 = torch.autograd.grad((b0 @ a0 @ x) @ g, (a0, b0))
        self.close(ga0, torch.zeros_like(a0)); self.close(gb0, torch.zeros_like(b0))

    def test_26_top1_renormalized_gate_has_zero_task_gradient(self):
        logits = nn.Parameter(torch.tensor([.2, 1., -.4], dtype=DTYPE))
        probabilities = logits.softmax(-1)
        selected = probabilities[torch.argmax(probabilities)]
        renormalized = selected/selected
        gradient, = torch.autograd.grad(renormalized*3, logits)
        self.close(gradient, torch.zeros_like(logits))
        # 没有“在选中集合内重归一化”时，选中概率仍可获得梯度。
        probabilities = logits.softmax(-1)
        gradient2, = torch.autograd.grad(probabilities[1]*3, logits)
        self.assertGreater(gradient2.norm().item(), 0.)

    def test_27_dpo_equal_reference_loss_and_gradient(self):
        chosen = torch.tensor(-3., dtype=DTYPE, requires_grad=True)
        rejected = torch.tensor(-4., dtype=DTYPE, requires_grad=True)
        beta = .2
        loss = dpo_loss(chosen, rejected, chosen.detach(), rejected.detach(), beta)
        gc, gr = torch.autograd.grad(loss, (chosen, rejected))
        self.close(loss, math.log(2)); self.close(gc, -beta/2); self.close(gr, beta/2)

    def test_28_dpo_reward_partition_and_sequence_sum(self):
        ref = torch.tensor([.2, .3, .5], dtype=DTYPE)
        rewards = torch.tensor([1., 2., -1.], dtype=DTYPE)
        beta = .7
        optimal = (ref.log()+rewards/beta).softmax(0)
        recovered = beta*(optimal.log()-ref.log())
        self.close(recovered[0]-recovered[1], rewards[0]-rewards[1])
        self.close((ref.log()+(rewards+10)/beta).softmax(0), optimal)
        # 两条序列的逐 token 对数比同为 0.1，长度不同；求和与均值目标不同。
        chosen = torch.tensor([.1, .1, .1], dtype=DTYPE)
        rejected = torch.tensor([.1], dtype=DTYPE)
        self.close(chosen.sum()-rejected.sum(), .2)
        self.close(chosen.mean()-rejected.mean(), 0.)

    def test_29_grpo_group_mean_bias_and_leave_one_out(self):
        # 二元动作 a~Bernoulli(p)，奖励 r=a，logit 得分梯度 a-p。
        p = .3
        expected_centered = expected_loo = 0.
        for a, b in itertools.product((0., 1.), repeat=2):
            probability = (p if a else 1-p)*(p if b else 1-p)
            rewards = torch.tensor([a, b], dtype=DTYPE)
            scores = rewards-p
            expected_centered += probability*(centered_advantage(rewards)*scores).mean().item()
            expected_loo += probability*(centered_advantage(rewards, leave_one_out=True)*scores).mean().item()
        true_gradient = p*(1-p)
        self.assertAlmostEqual(expected_centered, true_gradient/2, places=12)
        self.assertAlmostEqual(expected_loo, true_gradient, places=12)

    def test_30_constant_reward_advantage_zero(self):
        r = torch.ones(4, dtype=DTYPE)
        adv = centered_advantage(r)
        normalized = adv/(r.std(unbiased=False)+1e-8)
        self.close(normalized, torch.zeros_like(r))

    def test_31_speculative_exact_distribution_reconstruction(self):
        p = torch.tensor([.6, .4], dtype=DTYPE)
        q = torch.tensor([.2, .8], dtype=DTYPE)
        accepted, reject, residual = speculative_masses(p, q)
        self.close(accepted, [.2, .4]); self.close(reject, .4); self.close(residual, [1., 0.])
        self.close(accepted+reject*residual, p)
        self.close(accepted.sum(), 1-(p-q).abs().sum()/2)

    def test_32_speculative_zero_proposal_and_equal_distributions(self):
        p = torch.tensor([.5, .5], dtype=DTYPE)
        q = torch.tensor([0., 1.], dtype=DTYPE)
        accepted, reject, residual = speculative_masses(p, q)
        self.close(accepted+reject*residual, p)
        a, r, correction = speculative_masses(p, p)
        self.close(a, p); self.close(r, 0.)
        self.assertTrue(torch.isfinite(correction).all())

    def test_33_conformal_order_and_infinite_boundary(self):
        scores = [9., 1., 5., 2., 8., 3., 7., 4., 6.]
        self.assertEqual(conformal_quantile(scores, .2), 8.)
        self.assertTrue(math.isinf(conformal_quantile(scores, .01)))
        with self.assertRaises(ValueError):
            conformal_quantile([], .1)

    def test_34_pass_at_k_matches_subset_enumeration(self):
        outcomes = [1, 1, 0, 0, 0]
        subsets = list(itertools.combinations(outcomes, 2))
        exact = sum(any(s) for s in subsets)/len(subsets)
        self.assertAlmostEqual(pass_at_k(5, 2, 2), exact)
        self.assertAlmostEqual(exact, .7)

    def test_35_ctc_path_sum_matches_torch(self):
        paths = list(itertools.product((0, 1), repeat=2))
        probability = sum(.25 for path in paths if ctc_collapse(path) == (1,))
        self.assertAlmostEqual(probability, .75)
        log_probs = torch.full((2, 1, 2), math.log(.5), dtype=DTYPE)
        loss = F.ctc_loss(log_probs, torch.tensor([1]), torch.tensor([2]), torch.tensor([1]), reduction='none')
        self.close(loss, [-math.log(.75)])
        self.assertEqual(ctc_collapse([1, 0, 1]), (1, 1))
        self.assertEqual(ctc_collapse([1, 1]), (1,))

    def test_36_ctc_impossible_repeat_alignment(self):
        log_probs = torch.full((2, 1, 2), math.log(.5), dtype=DTYPE)
        loss = F.ctc_loss(log_probs, torch.tensor([1, 1]), torch.tensor([2]), torch.tensor([2]), reduction='none')
        self.assertTrue(torch.isinf(loss).all())
        zeroed = F.ctc_loss(log_probs, torch.tensor([1, 1]), torch.tensor([2]), torch.tensor([2]), reduction='none', zero_infinity=True)
        self.close(zeroed, [0.])

    def test_37_diffusion_conditional_score_and_reconstruction(self):
        clean = torch.randn(4, dtype=DTYPE)
        noise = torch.randn(4, dtype=DTYPE)
        alpha, sigma = .8, .6
        noisy = (alpha*clean+sigma*noise).requires_grad_()
        log_density = -(noisy-alpha*clean).square().sum()/(2*sigma**2)
        gradient, = torch.autograd.grad(log_density, noisy)
        self.close(gradient, -noise/sigma)
        self.close((noisy-sigma*noise)/alpha, clean)

    def test_38_flow_matching_conditional_velocity(self):
        z = torch.randn(5, dtype=DTYPE)
        x = torch.randn(5, dtype=DTYPE)
        t, h = .4, 1e-5
        path = lambda u: (1-u)*z+u*x
        self.close((path(t+h)-path(t-h))/(2*h), x-z, atol=1e-10)
        self.close(path(0), z); self.close(path(1), x)

    def test_39_classifier_free_guidance_convention(self):
        unconditional = torch.tensor([1., 2.], dtype=DTYPE)
        conditional = torch.tensor([3., 1.], dtype=DTYPE)
        guided = lambda w: unconditional+w*(conditional-unconditional)
        self.close(guided(0), unconditional)
        self.close(guided(1), conditional)
        self.close(guided(2), [5., 0.])

    def test_40_vector_conditional_bias_variance_uses_trace(self):
        values = torch.tensor([[1., 2.], [3., 0.], [2., 4.]], dtype=DTYPE)
        prediction = torch.tensor([.5, 1.], dtype=DTYPE)
        mean = values.mean(0)
        centered = values-mean
        covariance = centered.T @ centered / len(values)
        actual = (values-prediction).square().sum(-1).mean()
        self.close(actual, covariance.trace()+(mean-prediction).square().sum())

    def test_41_linear_regression_residual_orthogonality(self):
        x = torch.tensor([[1.], [2.]], dtype=DTYPE)
        y = torch.tensor([1., 3.], dtype=DTYPE)
        solution = torch.linalg.lstsq(x, y).solution
        self.close(solution, [1.4])
        self.close(x.T @ (y-x@solution), [0.])

    def test_42_cross_entropy_kl_decomposition(self):
        p = torch.tensor([.8, .2], dtype=DTYPE)
        q = torch.tensor([.6, .4], dtype=DTYPE)
        entropy = -(p*p.log()).sum()
        ce = -(p*q.log()).sum()
        kl = (p*(p.log()-q.log())).sum()
        self.close(ce, entropy+kl)
        self.assertGreaterEqual(kl.item(), 0.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
