"""运行：python -m unittest discover -s . -p 'test_*.py' -v。"""
import unittest
import torch
from torch import nn
from torch.nn import functional as F
from core_checks import online_attention, cached_causal_mask, ctc_collapse

class CoreTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17)
        torch.set_num_threads(1)

    def test_broadcasting_trap(self):
        prediction = torch.arange(4.).reshape(4, 1)
        target = torch.arange(4.)
        self.assertEqual((prediction-target).shape, (4, 4))
        self.assertEqual((prediction-target[:, None]).square().mean().item(), 0.)

    def test_view_and_copy(self):
        x = torch.arange(6.).reshape(2, 3)
        x.T[0, 1] = 99
        self.assertEqual(x[1, 0].item(), 99.)
        y = x.clone(); y[0, 0] = -7
        self.assertEqual(x[0, 0].item(), 0.)

    def test_scalar_autograd(self):
        x, w, b = [torch.tensor(v, requires_grad=True) for v in (2., 3., 1.)]
        loss = ((w*x+b)-5).square()/2
        loss.backward()
        self.assertEqual([loss.item(), w.grad.item(), b.grad.item(), x.grad.item()],
                         [2., 4., 2., 6.])

    def test_gradcheck(self):
        x = torch.randn(3, dtype=torch.double, requires_grad=True)
        self.assertTrue(torch.autograd.gradcheck(lambda z: (z.sin()*z).sum(), (x,)))

    def test_parameter_registration(self):
        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.layers = nn.ModuleList([nn.Linear(2, 3), nn.Linear(3, 1)])
                self.register_buffer('scale', torch.ones(1))
        model = Net()
        self.assertEqual(sum(p.numel() for p in model.parameters()), 13)
        self.assertIn('scale', model.state_dict())
        self.assertNotIn('scale', dict(model.named_parameters()))

    def test_convolution_example(self):
        x = torch.arange(1., 10.).reshape(1, 1, 3, 3)
        kernel = torch.tensor([[1., 0.], [0., -1.]]).reshape(1, 1, 2, 2)
        torch.testing.assert_close(F.conv2d(x, kernel), torch.full((1, 1, 2, 2), -4.))

    def test_convolution_shape_parameters(self):
        layer = nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1)
        self.assertEqual(layer(torch.randn(2, 3, 32, 32)).shape, (2, 16, 16, 16))
        self.assertEqual(sum(p.numel() for p in layer.parameters()), 448)

    def test_receptive_field(self):
        radius, jump = 1, 1
        values = []
        for kernel, stride in [(3, 2), (3, 2), (3, 1)]:
            radius += (kernel-1)*jump
            jump *= stride
            values.append((radius, jump))
        self.assertEqual(values, [(3, 2), (7, 4), (15, 4)])

    def test_cnn_data_config_and_seed(self):
        from train_cnn import make_data
        a, b = make_data(8, 11), make_data(8, 11)
        self.assertTrue(torch.equal(a.tensors[0], b.tensors[0]))
        exact = make_data(2, 11, noise=0, position_min=4, position_max=4)
        self.assertEqual(exact.tensors[0][0, 0, 4, 2:14].tolist(), [1.] * 12)
        self.assertEqual(exact.tensors[0][1, 0, 2:14, 4].tolist(), [1.] * 12)
        for kwargs in [dict(noise=float('nan')), dict(noise=float('inf')),
                       dict(noise=-1), dict(position_min=-1), dict(position_max=16),
                       dict(position_min=10, position_max=9)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                make_data(2, 11, **kwargs)

    def test_cnn_shapes_and_parameter_ledger(self):
        from train_cnn import build_model
        model = build_model()
        self.assertEqual([sum(p.numel() for p in model[i].parameters()) for i in [0, 2, 6]],
                         [80, 1168, 34])
        x = torch.zeros(1, 1, 16, 16)
        shapes, byte_counts = [list(x.shape)], [x.numel() * x.element_size()]
        for i, layer in enumerate(model):
            x = layer(x)
            if i in [0, 2, 4, 6]:
                shapes.append(list(x.shape)); byte_counts.append(x.numel() * x.element_size())
        self.assertEqual(shapes, [[1, 1, 16, 16], [1, 8, 16, 16], [1, 16, 16, 16],
                                  [1, 16, 1, 1], [1, 2]])
        self.assertEqual(byte_counts, [1024, 8192, 16384, 64, 8])

    def test_cnn_visual_report_interface(self):
        import tempfile
        from pathlib import Path
        import xml.etree.ElementTree as ET
        from train_cnn import write_visuals
        sample = {'index': 0, 'label': 0, 'prediction': 1, 'pixels': [[0.] * 16 for _ in range(16)]}
        report = {'history': [{'epoch': 1, 'train_loss': .7, 'validation': {'loss': .8}},
                              {'epoch': 2, 'train_loss': .4, 'validation': {'loss': .6}}],
                  'samples': [sample], 'error_samples': [sample]}
        with tempfile.TemporaryDirectory(prefix='cnn-visual-fixture-') as directory:
            output = Path(directory)
            write_visuals(report, output)
            for name in ['history.svg', 'samples.svg']:
                root = ET.fromstring((output / name).read_text())
                self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
            history = (output / 'history.svg').read_text()
            self.assertIn('blue=train, red=validation', history)
            self.assertIn('epoch 2', history)
            self.assertIn('y=0 p=1', (output / 'samples.svg').read_text())

    def test_residual_jacobian(self):
        x = torch.tensor(2., requires_grad=True)
        y = x+x*x
        y.backward()
        self.assertEqual(x.grad.item(), 5.)

    def test_online_attention(self):
        q, k, v = (torch.randn(*shape, dtype=torch.double) for shape in
                    [(4, 5), (11, 5), (11, 7)])
        expected = (q @ k.T/5**0.5).softmax(-1) @ v
        for block in [1, 3, 20]:
            torch.testing.assert_close(online_attention(q, k, v, block), expected,
                                       rtol=1e-11, atol=1e-11)

    def test_online_attention_large_logits(self):
        q = torch.tensor([[1000., -1000.]], dtype=torch.double)
        k = torch.tensor([[10., 1.], [9., -1.], [-10., 2.]], dtype=torch.double)
        v = torch.randn(3, 4, dtype=torch.double)
        result = online_attention(q, k, v, 2)
        self.assertTrue(torch.isfinite(result).all())
        torch.testing.assert_close(result, (q @ k.T/2**0.5).softmax(-1) @ v)

    def test_online_attention_invalid(self):
        with self.assertRaises(ValueError):
            online_attention(torch.ones(2, 3), torch.ones(4, 3), torch.ones(4, 1), 0)

    def test_offset_causal_mask(self):
        expected = torch.tensor([[1, 1, 1, 1, 1, 1, 0], [1, 1, 1, 1, 1, 1, 1]], dtype=torch.bool)
        self.assertTrue(torch.equal(cached_causal_mask(5, 2), expected))

    def test_cached_attention_matches_full(self):
        q, k, v = [torch.randn(1, 2, 7, 4, dtype=torch.double) for _ in range(3)]
        full = F.scaled_dot_product_attention(q, k, v, dropout_p=0., is_causal=True)
        cached = F.scaled_dot_product_attention(q[:, :, 5:], k, v,
                     attn_mask=cached_causal_mask(5, 2), dropout_p=0., is_causal=False)
        torch.testing.assert_close(cached, full[:, :, 5:], atol=1e-12, rtol=1e-12)

    def test_mla_absorption(self):
        c, up_k, up_v, q = [torch.randn(*shape, dtype=torch.double) for shape in
                            [(7, 3), (5, 3), (4, 3), (2, 5)]]
        weights = (q @ (c @ up_k.T).T/5**0.5).softmax(-1)
        expanded = weights @ (c @ up_v.T)
        absorbed_weights = ((q @ up_k) @ c.T/5**0.5).softmax(-1)
        absorbed = (absorbed_weights @ c) @ up_v.T
        torch.testing.assert_close(expanded, absorbed, atol=1e-12, rtol=1e-12)

    def test_global_token_average(self):
        sums, counts = [8., 6.], [8, 2]
        global_mean = sum(sums)/sum(counts)
        mean_of_means = sum(s/n for s, n in zip(sums, counts))/2
        scaled_ddp = sum(2*s/sum(counts) for s in sums)/2
        self.assertAlmostEqual(global_mean, 1.4)
        self.assertAlmostEqual(mean_of_means, 2.)
        self.assertAlmostEqual(scaled_ddp, global_mean)

    def test_ctc_order(self):
        self.assertEqual(ctc_collapse([1, 1, 0, 1]), [1, 1])
        self.assertEqual(ctc_collapse([0, 0, 1, 2, 2, 0]), [1, 2])

    def test_diffusion_identity(self):
        x0 = torch.randn(8, dtype=torch.double)
        eps = torch.randn_like(x0)
        alpha_bar = torch.tensor(0.64, dtype=torch.double)
        xt = alpha_bar.sqrt()*x0 + (1-alpha_bar).sqrt()*eps
        reconstructed = (xt-(1-alpha_bar).sqrt()*eps)/alpha_bar.sqrt()
        torch.testing.assert_close(reconstructed, x0)

    def test_flow_path(self):
        noise, data = torch.randn(3), torch.randn(3)
        velocity = data-noise
        torch.testing.assert_close(noise+velocity, data)
        # 这里只验证配对条件路径，不代表学到的边缘速度场是一条直线。

    def test_cross_entropy_logits(self):
        logits = torch.tensor([[2., 1., -1.]], dtype=torch.double)
        target = torch.tensor([0])
        torch.testing.assert_close(F.cross_entropy(logits, target),
                                   -logits.log_softmax(-1)[0, 0])

if __name__ == '__main__':
    unittest.main()
