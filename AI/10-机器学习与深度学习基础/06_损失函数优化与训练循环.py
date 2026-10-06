from __future__ import annotations

try:
    import torch
except ModuleNotFoundError:
    print("SKIP: 需要已安装的 CPU PyTorch 才能运行本示例；未下载任何依赖。")
    raise SystemExit(77)

torch.manual_seed(7)
torch.set_num_threads(1)
x = torch.arange(8, dtype=torch.float32).reshape(-1, 1)
y = 3.0 * x + 1.0

model = torch.nn.Linear(1, 1)
criterion = torch.nn.MSELoss()
optimizer = torch.optim.SGD(model.parameters(), lr=0.03)

model.train()
for _ in range(800):
    optimizer.zero_grad()
    prediction = model(x)
    loss = criterion(prediction, y)
    loss.backward()
    optimizer.step()

model.eval()
with torch.no_grad():
    final_loss = criterion(model(x), y).item()
    weight = model.weight.item()
    bias = model.bias.item()

print(f"mse={final_loss:.8f}, weight={weight:.4f}, bias={bias:.4f}")
assert final_loss < 1e-4
assert abs(weight - 3.0) < 0.02
assert abs(bias - 1.0) < 0.08
print("训练循环检查通过：参数学到了玩具数据的线性关系。")
