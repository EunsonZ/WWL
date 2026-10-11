---
type: lab
domain: artificial-intelligence
stage: 2
aliases:
  - 有限图消息与结构碰撞复算
prerequisites:
  - "[[AI/16-图表示学习/01-图对象消息传递与学习目标]]"
  - "[[AI/16-图表示学习/02-消息传递表达能力与结构反例]]"
sources:
  - https://proceedings.mlr.press/v70/gilmer17a.html
  - https://arxiv.org/abs/1810.00826
---

# 有限图消息传递与表示限制

本实践核对 [[AI/16-图表示学习/01-图对象消息传递与学习目标|三节点消息、损失和梯度]] 与 [[AI/16-图表示学习/02-消息传递表达能力与结构反例|结构碰撞及变条件]] 的同一组输入。[gnn_toy.py](gnn_toy.py) 是规范源码，只使用 Python 3 标准库；全部图、特征和标签为固定合成输入，不下载数据或训练真实模型。默认仅输出 JSON；只有明确给 `--output-dir` 才生成两张 SVG。

## 先预测再运行

从本页目录执行：

```bash
python3 -B gnn_toy.py
python3 -B gnn_toy.py --weight 2 --depth 3
python3 -B gnn_toy.py --weight -1
python3 -B gnn_toy.py --depth 0
python3 -B gnn_toy.py --output-dir /private/tmp/wwl-gnn-reader-figures
```

最后一条的目录必须尚不存在，已存在路径会拒绝，避免覆盖原图或别人的结果；重复生成请另选一个新目录。`--weight`、`--target`、`--constant` 要有限且在 `[-10,10]`，`--learning-rate` 在 `[0,1]`，`--depth` 为0到32的整数。限制计算规模是实现边界，不是理论深度上限。API只支持无向无权、零对角的输入邻接；带自环的均值由层内部构造。多列节点特征与权重的 shape 在 `validate_graph/mean_layer` 检查；重复边、越界端点、非置换顺序和非有限输入均拒绝。

| 情形 | 应观察到的字段 | 解释边界 |
| --- | --- | --- |
| 默认 | path.hidden=`[[.5],[1],[1]]`，prediction=2.5，loss=.125，gradient=1.25，new_weight=.875，after_prediction=2.1875，after_loss=.017578125 | 一个图标签的一次更新，不是泛化试验 |
| 反转编号 | permuted_hidden=`[[1],[1],[.5]]`，permuted_prediction=2.5；bad读出从1变2 | 正确同步变换保持等变，编号优先选择破坏它 |
| constant=1、weight=1、depth=4 | 两图每层各节点都1，readout均为`[6]` | 有限实跑核实现，任意参数/深度由正文归纳证明 |
| weight=2、depth=3 | 结构节点各为8，两图readout均`[48]`；path梯度7.5，更新weight=1.25、after_prediction=3.125 | 同一个参数用于路径和结构演示，仍有不同任务职责 |
| weight=-1 | 本例正初值经ReLU变0，path.gradient=0 | 不能照抄正分支梯度 |
| 新增三角形计数 | triangle_features为六份0或六份1；triangle_readout_at_weight1为`[0]`与`[6]` | 固定使用一层W=1；输入信息已改变，与CLI原weight分开 |

源码数组采用0起始索引；正文和SVG节点标签采用1起始。`order[i]` 表示新行 $i$ 取旧行 `order[i]`。SVG边来自相同的邻接，数值来自同一个 JSON report；坐标仅为排版，不是输入特征。固定读者图为 [三节点图](figures/path3.svg) 与 [结构碰撞图](figures/structure_collision.svg)，生成条件是默认参数。改变参数重新生成时，必须保留同一次输入、输出和图，不用默认图说明另一组数字。

## 运行证据与仍未验证的层

2026-10-12，非作者以独立 Fraction 标量/矩阵与 BFS 路线实际复核：13种CLI（默认、改变权重/目标/学习率/深度/初值、非法参数与既有输出目录保护），8类非法API、三节点全部6种置换、两图脉冲输入的0至12步状态、有限差分梯度；默认、变条件、允许极值的6张SVG实际渲染并目视，无裁切。正文固定两图来自该最终源码的默认输出。这支持列出的有限计算与生成行为，未运行旧的隐藏单元源码、重训练、真实图数据评测或Obsidian客户端；没有真人保持/迁移结果。

独立运行原始输出保存在本次临时运行目录 `/private/tmp/wwl-stage-gnn-foundations-runner-20261012/final/`，它是运行记录的位置，不是长期阅读依赖；规范源码、固定输入（在源码中）与本页步骤可重新生成结果。未来运行须另注明实际环境和结果，不能把本次记录写成新一轮已跑。重要理论结论还由正文完整归纳和独立论证核查承担。

## 规范源码镜像

下列代码逐字对应同目录执行文件，镜像供阅读，不是另一份独立实现。

<!-- code-sync: ./gnn_toy.py -->
```python
"""有限无向图教学：行均值消息、一次梯度、重编号与结构碰撞。标准库。"""
from __future__ import annotations

import argparse
from html import escape
import json
import math
from pathlib import Path


def adjacency(n, edges):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    a = [[0.0] * n for _ in range(n)]
    seen = set()
    for edge in edges:
        if len(edge) != 2:
            raise ValueError("each edge needs two endpoints")
        u, v = edge
        if any(isinstance(k, bool) or not isinstance(k, int) or not 0 <= k < n for k in edge):
            raise ValueError("edge endpoint outside graph")
        if u == v:
            raise ValueError("input graph has no self loops")
        key = tuple(sorted((u, v)))
        if key in seen:
            raise ValueError("duplicate edge")
        seen.add(key)
        a[u][v] = a[v][u] = 1.0
    return a


def validate_graph(a, x):
    n = len(a)
    if not n or any(len(row) != n for row in a):
        raise ValueError("adjacency must be nonempty and square")
    if any(isinstance(v, bool) or v not in (0, 1) for row in a for v in row):
        raise ValueError("only unweighted 0/1 adjacency supported")
    if any(a[i][i] != 0 or a[i][j] != a[j][i] for i in range(n) for j in range(n)):
        raise ValueError("input must be symmetric and have zero diagonal")
    if len(x) != n or not x or not x[0] or any(len(row) != len(x[0]) for row in x):
        raise ValueError("node features must have shape n by d with d >= 1")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for row in x for v in row):
        raise ValueError("features must be finite real numbers")


def mean_layer(a, x, w):
    validate_graph(a, x)
    d = len(x[0])
    if len(w) != d or not w or not w[0] or any(len(row) != len(w[0]) for row in w):
        raise ValueError("weight must have shape d by k with k >= 1")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for row in w for v in row):
        raise ValueError("weights must be finite real numbers")
    n, k = len(a), len(w[0])
    mean = [[sum((a[i][j] + (i == j)) * x[j][c] for j in range(n)) /
             (1 + sum(a[i])) for c in range(d)] for i in range(n)]
    z = [[sum(mean[i][c] * w[c][b] for c in range(d)) for b in range(k)] for i in range(n)]
    return {"mean": mean, "preactivation": z, "hidden": [[max(0.0, v) for v in row] for row in z]}


def relabel(a, x, order):
    validate_graph(a, x)
    if any(isinstance(i, bool) or not isinstance(i, int) for i in order) or sorted(order) != list(range(len(a))):
        raise ValueError("order must be a permutation; new row i takes old row order[i]")
    return [[a[i][j] for j in order] for i in order], [list(x[i]) for i in order]


def first_neighbor(a, x):
    validate_graph(a, x)
    out = []
    for row in a:
        neighbors = [j for j, present in enumerate(row) if present]
        out.append(list(x[neighbors[0]]) if neighbors else [0.0] * len(x[0]))
    return out


def readout(x):
    return [sum(row[c] for row in x) for c in range(len(x[0]))]


def triangle_counts(a):
    # (A^3)_ii / 2: each incident triangle gives two closed length-three walks.
    return [[sum(a[i][j] * a[j][k] * a[k][i] for j in range(len(a)) for k in range(len(a))) / 2]
            for i in range(len(a))]


def path_case(weight, target, learning_rate):
    a = adjacency(3, [(0, 1), (1, 2)])
    x = [[1.0], [0.0], [2.0]]
    result = mean_layer(a, x, [[weight]])
    prediction = readout(result["hidden"])[0]
    # At a ReLU kink choose derivative 0; lesson's differentiable branch has weight > 0.
    slope = sum(result["mean"][i][0] for i in range(3) if result["preactivation"][i][0] > 0)
    gradient = (prediction - target) * slope
    new_weight = weight - learning_rate * gradient
    after = mean_layer(a, x, [[new_weight]])
    order = [2, 1, 0]
    ap, xp = relabel(a, x, order)
    permuted = mean_layer(ap, xp, [[weight]])
    bad, badp = first_neighbor(a, x), first_neighbor(ap, xp)
    return {"adjacency": a, "features": x, "weight": weight, "target": target,
            "learning_rate": learning_rate, **result, "prediction": prediction,
            "loss": (prediction - target) ** 2 / 2, "gradient": gradient,
            "new_weight": new_weight, "after_hidden": after["hidden"],
            "after_prediction": readout(after["hidden"])[0],
            "after_loss": (readout(after["hidden"])[0] - target) ** 2 / 2,
            "order": order, "permuted_adjacency": ap, "permuted_features": xp,
            "permuted_hidden": permuted["hidden"], "permuted_prediction": readout(permuted["hidden"])[0],
            "bad_hidden": bad, "bad_permuted_hidden": badp,
            "bad_prediction": readout(bad)[0], "bad_permuted_prediction": readout(badp)[0]}


def structure_case(depth, constant, weight):
    graphs = {"cycle6": adjacency(6, [(i, (i + 1) % 6) for i in range(6)]),
              "two_triangles": adjacency(6, [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])}
    out = {}
    for name, a in graphs.items():
        h = [[constant] for _ in a]
        history = [h]
        for _ in range(depth):
            h = mean_layer(a, h, [[weight]])["hidden"]
            history.append(h)
        tri = triangle_counts(a)
        out[name] = {"adjacency": a, "initial": history[0], "history": history,
                     "readout": readout(h), "triangle_features": tri,
                     "triangle_readout_at_weight1": readout(mean_layer(a, tri, [[1.0]])["hidden"])}
    return out


def draw_graph(a, x, positions, offset, title, value_label):
    parts = [f'<text x="{offset+20}" y="40" font-size="21" font-weight="bold">{escape(title)}</text>']
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            if a[i][j]:
                p, q = positions[i], positions[j]
                parts.append(f'<line x1="{offset+p[0]}" y1="{p[1]}" x2="{offset+q[0]}" y2="{q[1]}" stroke="#536273" stroke-width="3"/>')
    for i, (px, py) in enumerate(positions):
        parts.append(f'<circle cx="{offset+px}" cy="{py}" r="25" fill="#e8f1fa" stroke="#195a83" stroke-width="2"/>')
        parts.append(f'<text x="{offset+px}" y="{py+6}" text-anchor="middle" font-size="18">{i+1}</text>')
        parts.append(f'<text x="{offset+px}" y="{py+48}" text-anchor="middle" font-size="16">{escape(value_label)}={x[i][0]:g}</text>')
    return parts


def render_figures(report, output_dir):
    # Refuse an existing destination so source/results cannot be silently overwritten.
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=False)
    base = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" role="img"><title>{}</title><desc>{}</desc><rect width="900" height="420" fill="white"/><g font-family="sans-serif" fill="#1d2b36">'
    p = report["path"]
    parts = [base.format('Path3: features and one message layer', 'Same edges and node order before and after. Positions are layout only, not model features.')]
    positions = [(80, 160), (220, 160), (360, 160)]
    parts += draw_graph(p["adjacency"], p["features"], positions, 0, 'Input: x', 'x')
    parts += draw_graph(p["adjacency"], p["hidden"], positions, 450, 'Row mean + W + ReLU', 'h')
    parts += [f'<text x="25" y="290" font-size="18">W={p["weight"]:g}; graph sum={p["prediction"]:g}; target={p["target"]:g}</text>',
              f'<text x="25" y="330" font-size="18">gradient={p["gradient"]:g}; new W={p["new_weight"]:g}; new sum={p["after_prediction"]:g}</text>',
              '<text x="25" y="380" font-size="16">Dimensionless; layout is not X. Self loops belong to propagation.</text></g></svg>']
    (destination / 'path3.svg').write_text('\n'.join(parts), encoding='utf-8')
    s = report["structure"]
    parts = [base.format('Cycle6 and two triangles: identical constant node inputs', 'Both graphs have six nodes and degree two. Layout reveals components to readers but is not supplied to the model.')]
    cycle = [(220+105*math.cos(i*math.pi/3), 180+90*math.sin(i*math.pi/3)) for i in range(6)]
    triangles = [(75,120),(175,120),(125,220),(275,120),(375,120),(325,220)]
    for name, pos, off, title in [('cycle6',cycle,0,'C6'),('two_triangles',triangles,450,'Two triangles')]:
        parts += draw_graph(s[name]['adjacency'], s[name]['initial'], pos, off, title, 'x')
        parts.append(f'<text x="{off+20}" y="330" font-size="18">{report["depth"]} layers, W={p["weight"]:g}: sum={s[name]["readout"][0]:g}</text>')
        parts.append(f'<text x="{off+20}" y="365" font-size="16">triangle features, 1 layer W=1: sum={s[name]["triangle_readout_at_weight1"][0]:g}</text>')
    parts.append('<text x="20" y="405" font-size="14">Dimensionless; layout is not X. Triangle-count input changes the information available.</text></g></svg>')
    (destination / 'structure_collision.svg').write_text('\n'.join(parts), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weight', type=float, default=1.0)
    parser.add_argument('--target', type=float, default=2.0)
    parser.add_argument('--learning-rate', type=float, default=0.1)
    parser.add_argument('--depth', type=int, default=4)
    parser.add_argument('--constant', type=float, default=1.0)
    parser.add_argument('--output-dir', help='new directory for two SVGs; existing path is refused')
    args = parser.parse_args()
    if not all(math.isfinite(v) and abs(v) <= 10 for v in [args.weight, args.target, args.constant]):
        parser.error('weight, target and constant must be finite and within [-10,10]')
    if not math.isfinite(args.learning_rate) or not 0 <= args.learning_rate <= 1:
        parser.error('learning rate must be finite and within [0,1]')
    if not 0 <= args.depth <= 32:
        parser.error('depth must be within [0,32]')
    report = {'path': path_case(args.weight, args.target, args.learning_rate),
              'structure': structure_case(args.depth, args.constant, args.weight),
              'depth': args.depth, 'normalization': 'row mean with self loops',
              'units': 'synthetic dimensionless', 'layout_is_model_feature': False}
    if args.output_dir:
        try:
            render_figures(report, args.output_dir)
        except FileExistsError:
            parser.error('output directory already exists; choose a new directory')
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
```
