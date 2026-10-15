from __future__ import annotations

try:
    import torch
except ModuleNotFoundError:
    print("SKIP: 需要已安装的 CPU PyTorch 才能运行本示例；未下载任何依赖。")
    raise SystemExit(77)

features = torch.arange(6, dtype=torch.float32).reshape(2, 3)
bias = torch.tensor([10.0, 20.0, 30.0])
shifted = features + bias

print("features:", tuple(features.shape), features.tolist())
print("bias:", tuple(bias.shape), bias.tolist())
print("shifted:", tuple(shifted.shape), shifted.tolist())
assert shifted.tolist() == [[10.0, 21.0, 32.0], [13.0, 24.0, 35.0]]
print("广播检查通过：偏置按特征轴对齐。")
