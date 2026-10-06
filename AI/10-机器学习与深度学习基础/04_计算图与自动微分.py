from __future__ import annotations

try:
    import torch
except ModuleNotFoundError:
    print("SKIP: 需要已安装的 CPU PyTorch 才能运行本示例；未下载任何依赖。")
    raise SystemExit(77)

w = torch.tensor(2.0, requires_grad=True)
x = torch.tensor([1.0, 3.0])
target = torch.tensor([3.0, 7.0])
loss = ((w * x - target) ** 2).mean()
loss.backward()

print(f"loss={loss.item():.1f}, gradient={w.grad.item():.1f}")
assert w.grad is not None
assert abs(w.grad.item() - (-4.0)) < 1e-6
with torch.no_grad():
    w -= 0.1 * w.grad
print(f"一次 SGD 更新后的 w={w.item():.1f}")
assert abs(w.item() - 2.4) < 1e-6
