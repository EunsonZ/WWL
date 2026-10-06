"""核心公式的 CPU 教学实现；不替代生产注意力 kernel 或分布式实现。"""
from __future__ import annotations
import torch


def online_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor,
                     block_size: int = 3) -> torch.Tensor:
    """无掩码单头注意力。以在线 softmax 合并统计量，不形成完整得分矩阵。"""
    if q.ndim != 2 or k.ndim != 2 or v.ndim != 2:
        raise ValueError('q/k/v 必须为二维张量')
    if q.shape[1] != k.shape[1] or k.shape[0] != v.shape[0] or k.shape[0] == 0:
        raise ValueError('q/k/v 维度不兼容或键序列为空')
    if block_size <= 0:
        raise ValueError('block_size 必须为正整数')
    maximum = q.new_full((q.shape[0], 1), float('-inf'))
    denominator = q.new_zeros((q.shape[0], 1))
    numerator = q.new_zeros((q.shape[0], v.shape[1]))
    for start in range(0, k.shape[0], block_size):
        scores = q @ k[start:start + block_size].T / q.shape[1] ** 0.5
        updated = torch.maximum(maximum, scores.max(dim=-1, keepdim=True).values)
        old_scale = (maximum - updated).exp()
        weights = (scores - updated).exp()
        denominator = old_scale * denominator + weights.sum(dim=-1, keepdim=True)
        numerator = old_scale * numerator + weights @ v[start:start + block_size]
        maximum = updated
    return numerator / denominator


def cached_causal_mask(past_length: int, query_length: int) -> torch.Tensor:
    """返回 [Q, past+Q] 布尔可见性掩码；True 表示允许注意。"""
    if past_length < 0 or query_length <= 0:
        raise ValueError('past_length >= 0 且 query_length > 0')
    query_position = past_length + torch.arange(query_length)
    key_position = torch.arange(past_length + query_length)
    return key_position[None, :] <= query_position[:, None]


def ctc_collapse(tokens: list[int], blank: int = 0) -> list[int]:
    """先合并连续重复，再去掉 blank。操作次序是 CTC 的一部分。"""
    result: list[int] = []
    previous: int | None = None
    for token in tokens:
        if token != previous and token != blank:
            result.append(token)
        previous = token
    return result
