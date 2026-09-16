"""离线 CPU 横线/竖线分类教学。数据全为合成，不下载图像或预训练权重。"""
from __future__ import annotations
import argparse
import copy
import json
import tempfile
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


def make_data(count: int, seed: int) -> TensorDataset:
    g = torch.Generator().manual_seed(seed)
    labels = torch.arange(count) % 2
    x = torch.randn(count, 1, 16, 16, generator=g)*0.15
    positions = torch.randint(3, 13, (count,), generator=g)
    for i, (label, position) in enumerate(zip(labels.tolist(), positions.tolist())):
        if label == 0:
            x[i, 0, position, 2:14] += 1.
        else:
            x[i, 0, 2:14, position] += 1.
    return TensorDataset(x, labels)


def build_model() -> nn.Module:
    return nn.Sequential(nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(),
                         nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(),
                         nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(16, 2))


@torch.no_grad()
def evaluate(model: nn.Module, dataset: TensorDataset) -> dict[str, float]:
    model.eval()
    logits = model(dataset.tensors[0])
    labels = dataset.tensors[1]
    return {'loss': float(nn.functional.cross_entropy(logits, labels)),
            'accuracy': float((logits.argmax(-1) == labels).float().mean())}


def run(epochs: int, output: Path) -> dict:
    if epochs < 1:
        raise ValueError('epochs 必须 >= 1')
    torch.manual_seed(2026)
    torch.set_num_threads(1)
    train, valid, test = (make_data(n, seed) for n, seed in [(256, 11), (128, 22), (128, 33)])
    loader = DataLoader(train, batch_size=32, shuffle=True,
                        generator=torch.Generator().manual_seed(44), num_workers=0)
    model = build_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=0.001)
    history = []; best_loss = float('inf'); best = None; best_epoch = None
    for epoch in range(epochs):
        model.train(); loss_sum = 0.
        for x, y in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(x), y)
            loss.backward(); optimizer.step()
            loss_sum += float(loss.detach())*len(y)
        metrics = evaluate(model, valid)
        history.append({'epoch': epoch+1, 'train_loss': loss_sum/len(train), 'validation': metrics})
        if metrics['loss'] < best_loss:
            best_loss = metrics['loss']; best = copy.deepcopy(model.state_dict()); best_epoch = epoch+1
    assert best is not None
    model.load_state_dict(best)
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output/'model.pt'
    torch.save(best, checkpoint)
    restored = build_model()
    restored.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True))
    model.eval(); restored.eval()
    with torch.no_grad():
        torch.testing.assert_close(model(test.tensors[0]), restored(test.tensors[0]), atol=0, rtol=0)
    report = {'task': 'synthetic_horizontal_vertical_lines', 'device': 'cpu',
              'torch': torch.__version__, 'seed': 2026, 'epochs': epochs, 'selected_epoch': best_epoch,
              'split_sizes': {'train': 256, 'validation': 128, 'test': 128},
              'test': evaluate(restored, test), 'checkpoint_roundtrip_exact': True, 'history': history,
              'limits': '仅代表此合成分布与固定种子；不证明真实图像泛化或 GPU 性能。'}
    (output/'metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--output', type=Path, help='显式保存目录；不指定时使用运行结束自动清理的临时目录')
    args = parser.parse_args()
    if args.output is None:
        with tempfile.TemporaryDirectory(prefix='ai-cnn-') as temporary:
            result = run(args.epochs, Path(temporary))
    else:
        result = run(args.epochs, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
