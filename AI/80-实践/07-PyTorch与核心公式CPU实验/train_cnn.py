"""离线 CPU 横线/竖线分类教学。数据全为合成，不下载图像或预训练权重。"""
from __future__ import annotations
import argparse
import copy
import json
import math
import tempfile
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


def validate_data_config(noise: float, position_min: int, position_max: int) -> None:
    if not math.isfinite(noise) or noise < 0:
        raise ValueError('noise 必须是非负有限数')
    if type(position_min) is not int or type(position_max) is not int or not (0 <= position_min <= position_max < 16):
        raise ValueError('位置须满足整数 0 <= min <= max < 16，端点均包含')


def make_data(count: int, seed: int, noise: float = 0.15,
              position_min: int = 3, position_max: int = 12) -> TensorDataset:
    validate_data_config(noise, position_min, position_max)
    if type(count) is not int or count < 1:
        raise ValueError('count 必须是正整数')
    g = torch.Generator().manual_seed(seed)
    labels = torch.arange(count) % 2
    x = torch.randn(count, 1, 16, 16, generator=g)*noise
    positions = torch.randint(position_min, position_max + 1, (count,), generator=g)
    for i, (label, position) in enumerate(zip(labels.tolist(), positions.tolist())):
        if label == 0:
            x[i, 0, position, 2:14] += 1.
        else:
            x[i, 0, 2:14, position] += 1.
    if not torch.isfinite(x).all():
        raise ValueError('生成的 FP32 像素非有限；减小noise')
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


def write_visuals(report: dict, output: Path) -> None:
    history = report['history']
    maximum = max(max(row['train_loss'], row['validation']['loss']) for row in history)
    scale = maximum if maximum > 0 else 1.
    curves = []
    for role, color in [('train_loss', '#2255aa'), ('validation', '#aa4422')]:
        points = []
        for index, row in enumerate(history):
            loss = row[role] if role == 'train_loss' else row[role]['loss']
            x = 50 + 540 * index / max(1, len(history) - 1)
            y = 270 - 220 * loss / scale
            points.append(f'{x:.2f},{y:.2f}')
        curves.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{" ".join(points)}"/>')
        for point in points:
            px, py = point.split(',')
            curves.append(f'<circle cx="{px}" cy="{py}" r="2" fill="{color}"/>')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="340" viewBox="0 0 640 340">'
           '<rect width="640" height="340" fill="white"/><g font-family="sans-serif" font-size="14">'
           '<text x="40" y="25">Synthetic CNN: loss (blue=train, red=validation)</text>'
           f'<text x="10" y="55">{scale:.3g}</text><text x="20" y="275">0</text>'
           '<path d="M50 50 V270 H590" fill="none" stroke="black"/>'
           '<text x="50" y="300">epoch 1</text>'
           f'<text x="520" y="300">epoch {len(history)}</text>' + ''.join(curves) + '</g></svg>')
    (output / 'history.svg').write_text(svg, encoding='utf-8')
    tiles = []
    samples = report['samples'] + report['error_samples']
    for index, sample in enumerate(samples):
        left, top = (index % 4) * 180 + 10, (index // 4) * 195 + 30
        tiles.append(f'<text x="{left}" y="{top-8}">i={sample["index"]} y={sample["label"]} p={sample["prediction"]}</text>')
        for row, pixels in enumerate(sample['pixels']):
            for col, value in enumerate(pixels):
                # Display mapping only; raw, unclipped values stay in metrics.json.
                gray = round(255 * min(1., max(0., value)))
                tiles.append(f'<rect x="{left+col*10}" y="{top+row*10}" width="10" height="10" fill="rgb({gray},{gray},{gray})"/>')
    height = 30 + 195 * ((len(samples) + 3) // 4)
    (output / 'samples.svg').write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="730" height="{height}">'
        f'<rect width="730" height="{height}" fill="white"/><g font-family="sans-serif" font-size="13">'
        + ''.join(tiles) + '</g></svg>', encoding='utf-8')


def run(epochs: int, output: Path, *, noise: float = 0.15,
        position_min: int = 3, position_max: int = 12, seed: int = 2026,
        test_noise: float | None = None, test_position_min: int | None = None,
        test_position_max: int | None = None) -> dict:
    if epochs < 1:
        raise ValueError('epochs 必须 >= 1')
    validate_data_config(noise, position_min, position_max)
    if type(seed) is not int or not (2015 <= seed < 2**63):
        raise ValueError('seed 必须是 [2015, 2**63) 中的整数')
    test_config = (noise if test_noise is None else test_noise,
                   position_min if test_position_min is None else test_position_min,
                   position_max if test_position_max is None else test_position_max)
    validate_data_config(*test_config)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    # 默认仍为 train=11、valid=22、test=33、shuffle=44。
    split_seeds = {'train': seed - 2015, 'validation': seed - 2004, 'test': seed - 1993}
    train = make_data(256, split_seeds['train'], noise, position_min, position_max)
    valid = make_data(128, split_seeds['validation'], noise, position_min, position_max)
    test = make_data(128, split_seeds['test'], *test_config)
    loader = DataLoader(train, batch_size=32, shuffle=True,
                        generator=torch.Generator().manual_seed(seed - 1982), num_workers=0)
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
              'torch': torch.__version__, 'seed': seed, 'epochs': epochs, 'selected_epoch': best_epoch,
              'split_sizes': {'train': 256, 'validation': 128, 'test': 128},
              'test': evaluate(restored, test), 'checkpoint_roundtrip_exact': True, 'history': history,
              'limits': '仅代表此合成分布与固定种子；不证明真实图像泛化或 GPU 性能。'}
    report['config'] = {'image_shape': [1, 16, 16], 'noise': noise,
                        'position_inclusive': [position_min, position_max],
                        'test_noise': test_config[0], 'test_position_inclusive': list(test_config[1:]),
                        'split_seeds': split_seeds, 'shuffle_seed': seed - 1982}
    with torch.no_grad():
        logits = restored(test.tensors[0])
        predictions = logits.argmax(-1)
        labels = test.tensors[1]
        errors = (predictions != labels).nonzero(as_tuple=False).flatten().tolist()
    def inspect(index: int) -> dict:
        return {'index': index, 'label': int(labels[index]),
                'prediction': int(predictions[index]), 'logits': logits[index].tolist(),
                'pixels': test.tensors[0][index, 0].tolist()}
    # 报告均在验证选模完成后生成，不能反过来用于选epoch。
    report['predictions'] = predictions.tolist()
    report['error_indices'] = errors
    report['samples'] = [inspect(i) for i in range(min(8, len(test)))]
    report['error_samples'] = [inspect(i) for i in errors[:8]]
    report['parameters'] = sum(p.numel() for p in restored.parameters())
    serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    (output/'metrics.json').write_text(serialized, encoding='utf-8')
    write_visuals(report, output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--output', type=Path, help='显式保存目录；不指定时使用运行结束自动清理的临时目录')
    parser.add_argument('--noise', type=float, default=0.15)
    parser.add_argument('--position-min', type=int, default=3)
    parser.add_argument('--position-max', type=int, default=12)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--test-noise', type=float)
    parser.add_argument('--test-position-min', type=int)
    parser.add_argument('--test-position-max', type=int)
    args = parser.parse_args()
    options = dict(noise=args.noise, position_min=args.position_min,
                   position_max=args.position_max, seed=args.seed,
                   test_noise=args.test_noise, test_position_min=args.test_position_min,
                   test_position_max=args.test_position_max)
    if args.output is None:
        with tempfile.TemporaryDirectory(prefix='ai-cnn-') as temporary:
            result = run(args.epochs, Path(temporary), **options)
    else:
        result = run(args.epochs, args.output, **options)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
