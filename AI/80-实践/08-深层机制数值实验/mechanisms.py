"""CPU 教学算子：显式暴露目标、形状和边界，供 test_mechanisms.py 交叉核验。

这些实现不是生产推理内核，也不替代真实多机 DDP 或大型模型质量评测。
所有函数均不访问网络，不加载外部权重。
"""
from __future__ import annotations

import math
from collections.abc import Sequence
import torch
from torch import Tensor
import torch.nn.functional as F


def projection(x: Tensor, u: Tensor) -> Tensor:
    """将一维向量 x 正交投影到非零 u 张成的直线。"""
    if x.ndim != 1 or x.shape != u.shape:
        raise ValueError('x、u 必须是同形的一维向量')
    denominator = torch.dot(u, u)
    if not torch.isfinite(denominator) or denominator.item() <= 0:
        raise ValueError('投影方向必须有限且非零')
    return u * torch.dot(u, x) / denominator


def attention(q: Tensor, k: Tensor, v: Tensor, mask: Tensor | None = None) -> tuple[Tensor, Tensor]:
    """二维单头注意力，mask=True 表示允许；拒绝无可见 key 的整行。"""
    if q.ndim != 2 or k.ndim != 2 or v.ndim != 2:
        raise ValueError('示例仅接受二维 q/k/v')
    if q.shape[1] != k.shape[1] or k.shape[0] != v.shape[0] or q.shape[1] == 0:
        raise ValueError('q/k/v 维数不兼容')
    scores = q @ k.T / math.sqrt(q.shape[1])
    if mask is not None:
        if mask.dtype != torch.bool or mask.shape != scores.shape:
            raise ValueError('mask 须为与 scores 同形的布尔张量')
        if not mask.any(dim=-1).all():
            raise ValueError('此教学算子不定义全屏蔽行的概率分布')
        scores = scores.masked_fill(~mask, -torch.inf)
    probabilities = scores.softmax(dim=-1)
    return probabilities @ v, probabilities


def attention_vjp(q: Tensor, k: Tensor, v: Tensor, upstream: Tensor,
                  mask: Tensor | None = None) -> tuple[Tensor, Tensor, Tensor, Tensor]:
    """解析反向传播，返回 dQ、dK、dV、dScores。"""
    output, p = attention(q, k, v, mask)
    if upstream.shape != output.shape:
        raise ValueError('上游梯度必须与输出同形')
    dp = upstream @ v.T
    ds = p * (dp - (dp * p).sum(dim=-1, keepdim=True))
    scale = math.sqrt(q.shape[1])
    return ds @ k / scale, ds.T @ q / scale, p.T @ upstream, ds


class SiLUFunction(torch.autograd.Function):
    """x*sigmoid(x) 的教学 backward；保存输入以支持高阶求导。"""
    @staticmethod
    def forward(ctx, x: Tensor) -> Tensor:
        ctx.save_for_backward(x)
        return x * x.sigmoid()

    @staticmethod
    def backward(ctx, grad_output: Tensor) -> tuple[Tensor]:
        (x,) = ctx.saved_tensors
        s = x.sigmoid()
        return (grad_output * (s + x * s * (1-s)),)


def token_mean(loss_sums: Sequence[Tensor], valid_counts: Sequence[int]) -> Tensor | None:
    """累积窗口按有效 token 数归一化；全空窗口返回 None，调用方跳过更新。"""
    if not loss_sums or len(loss_sums) != len(valid_counts):
        raise ValueError('损失和与计数须非空且等长')
    if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in valid_counts):
        raise ValueError('计数必须是非负整数')
    count = sum(valid_counts)
    if count == 0:
        return None
    return sum(loss_sums) / count


def ddp_local_objective(local_sum: Tensor, global_count: int, world_size: int) -> Tensor:
    """在默认平均 rank 梯度的假设下，构造本地标量；这里只计算标量不通信。"""
    if global_count <= 0 or world_size <= 0:
        raise ValueError('全局计数与 world_size 必须为正')
    return local_sum * (world_size / global_count)


def cached_causal_mask(past_length: int, query_length: int, device=None) -> Tensor:
    if past_length < 0 or query_length <= 0:
        raise ValueError('past_length 非负，query_length 为正')
    queries = torch.arange(past_length, past_length + query_length, device=device)
    keys = torch.arange(past_length + query_length, device=device)
    return keys[None, :] <= queries[:, None]


def rope(x: Tensor, positions: Tensor, frequencies: Tensor) -> Tensor:
    """相邻两维成对的 RoPE：x 为 [T,2D]，positions 为 [T]。"""
    if x.ndim != 2 or x.shape[-1] % 2 or positions.shape != x.shape[:1]:
        raise ValueError('x 应为 [T,2D]，positions 应为 [T]')
    if frequencies.ndim != 1 or frequencies.numel() * 2 != x.shape[-1]:
        raise ValueError('频率数量应为特征维度的一半')
    angle = positions[:, None] * frequencies[None, :]
    pairs = x.reshape(x.shape[0], -1, 2)
    a, b = pairs[..., 0], pairs[..., 1]
    return torch.stack((a*angle.cos()-b*angle.sin(), a*angle.sin()+b*angle.cos()), dim=-1).flatten(1)


def linear_attention_recurrent(q: Tensor, k: Tensor, v: Tensor) -> Tensor:
    """正特征核注意力：输入已是 phi(q)/phi(k)，非 softmax 近似核。"""
    if q.ndim != 2 or q.shape != k.shape or v.ndim != 2 or v.shape[0] != q.shape[0]:
        raise ValueError('q/k/v 的形状不兼容')
    state = torch.zeros((k.shape[1], v.shape[1]), dtype=q.dtype, device=q.device)
    normalizer = torch.zeros(k.shape[1], dtype=q.dtype, device=q.device)
    result = []
    for query, key, value in zip(q, k, v):
        state = state + key[:, None] * value[None, :]
        normalizer = normalizer + key
        denominator = query @ normalizer
        if denominator.item() <= 0:
            raise ValueError('核注意力分母须为正')
        result.append(query @ state / denominator)
    return torch.stack(result)


def compose_affine(second: tuple[Tensor, Tensor], first: tuple[Tensor, Tensor]) -> tuple[Tensor, Tensor]:
    """返回 second(first(h)) 的矩阵与偏移。"""
    a2, b2 = second
    a1, b1 = first
    return a2 @ a1, a2 @ b1 + b2


def dpo_loss(logp_chosen: Tensor, logp_rejected: Tensor, ref_chosen: Tensor,
             ref_rejected: Tensor, beta: float = 0.1) -> Tensor:
    if beta <= 0 or not math.isfinite(beta):
        raise ValueError('beta 必须有限且为正')
    margin = (logp_chosen-ref_chosen) - (logp_rejected-ref_rejected)
    return -F.logsigmoid(beta*margin)


def centered_advantage(rewards: Tensor, *, leave_one_out: bool = False) -> Tensor:
    if rewards.ndim != 1 or rewards.numel() < 2:
        raise ValueError('组内至少需要两个奖励')
    if leave_one_out:
        baseline = (rewards.sum() - rewards) / (rewards.numel()-1)
    else:
        baseline = rewards.mean()
    return rewards - baseline


def speculative_masses(p: Tensor, q: Tensor) -> tuple[Tensor, Tensor, Tensor]:
    """单步投机采样的已接受质量、拒绝概率、残差分布；以精确枚举而非蒙特卡洛验证。"""
    if p.ndim != 1 or p.shape != q.shape or p.numel() == 0:
        raise ValueError('p/q 必须为同形非空概率向量')
    for vector in (p, q):
        if not torch.isfinite(vector).all() or (vector < 0).any():
            raise ValueError('概率必须有限且非负')
        if not torch.isclose(vector.sum(), vector.new_tensor(1.0), rtol=1e-7, atol=1e-9):
            raise ValueError('概率和须为 1')
    accepted = torch.minimum(p, q)
    residual_mass = (p-q).clamp_min(0)
    rejection = residual_mass.sum()
    residual = residual_mass / rejection if rejection.item() > 0 else torch.zeros_like(p)
    return accepted, rejection, residual


def conformal_quantile(scores: Sequence[float], alpha: float) -> float:
    if not 0 < alpha < 1 or not scores or not all(math.isfinite(s) for s in scores):
        raise ValueError('需要有限非空分数和 0 < alpha < 1')
    n = len(scores)
    # 采用向上取整的次序统计量，不对分数插值。
    raw = (n+1)*(1-alpha)
    k = math.ceil(raw)
    return math.inf if k > n else sorted(scores)[k-1]


def pass_at_k(n: int, c: int, k: int) -> float:
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError('要求 0 <= c <= n 且 1 <= k <= n')
    return 1.0 if n-c < k else 1.0-math.comb(n-c, k)/math.comb(n, k)


def ctc_collapse(path: Sequence[int], blank: int = 0) -> tuple[int, ...]:
    """先合并相邻重复，再删除 blank；不能交换这两步。"""
    merged = [item for i, item in enumerate(path) if i == 0 or item != path[i-1]]
    return tuple(item for item in merged if item != blank)
