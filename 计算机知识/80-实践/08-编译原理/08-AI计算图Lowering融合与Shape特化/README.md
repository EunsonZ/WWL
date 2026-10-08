---
type: lab
domain: computer-science
stage: 8
status: ready
difficulty: 进阶
estimated_minutes: 55
topics: [tensor-graph, lowering, fusion, dynamic-shape, guards]
tags: [computer-science/compiler, computer-science/ai-compiler, computer-science/practice]
---

# AI 计算图 Lowering、融合与 Shape 特化

## 目标

这个实验用纯 Python 元数据模型回答一个核心问题：`add -> relu` 看起来可以融合，编译器还必须证明什么？你将观察 shape 传播、连续布局、alias 独立性、side effect 顺序和动态 shape guard，再用未融合 reference executor 对照融合执行结果。稳定理论请从 [[计算机知识/70-编译原理/18-AI编译栈图捕获融合Shape与张量Kernel|AI 编译栈：图捕获、融合、Shape 与张量 Kernel]] 进入，通用优化合法性见 [[计算机知识/70-编译原理/10-优化Pass别名分析与阶段排序|优化 Pass、别名分析与阶段排序]]。

## 边界

- 只使用 Python 标准库；不导入 PyTorch、NumPy、CUDA，不需要 GPU，不下载任何依赖。
- `TensorMeta` 只表达 shape、layout 和 alias group；本实验只实现同 shape 的 elementwise `add/mul/relu`，没有冒充完整 broadcasting、device placement 或 kernel codegen。
- 动态维不会被默认当作已知。只有提供与声明不冲突的特化 shape 时才融合，执行前 guard 失配会明确抛出 `GuardFailure`。
- reference 数值相等只证明这些有限操作和测试样例；它不证明浮点重排在所有 dtype/硬件上等价，也不证明生产 AI 编译器正确。

## 运行

```bash
python3 -m unittest -v test_tensor_lowering.py
python3 tensor_lowering.py
```

演示的正常路径会显示 `legal` 融合判定、两个 `(2, 4)` shape guard，reference 与 lowered 输出相同。测试另外要求 layout、alias 和 side effect 分别给出稳定的阻断理由，而不是用一个模糊的 `cannot fuse`。

## 可观察流程

```text
Graph(inputs + Ops)
  -> infer_metadata: shape/layout/alias
  -> _plan_pair: pattern/use/effect/layout/alias/dynamic-shape
  -> LoweredGraph: fused op + explicit guards + decisions
  -> run_lowered: guard check
  -> compare with run_reference
```

这里的 guard 是特化假设的可执行表达，不是注释。如果实际 feed 是 `(3, 4)` 而专用版本要求 `(2, 4)`，正确做法是 guard 失败后回退/重编译；这个小实验通过抛异常把该边界暴露给调用者，不暗中使用错误 kernel。

### 一个 fused 节点实际分配了什么

```text
逻辑图：a,b → add → intermediate → ReLU → output
LoweredGraph：a,b → fused_add_relu → output
当前 Python 执行：_elementwise(a,b) → 完整 intermediate Tensor
                 → 逐元素 ReLU → 另一个完整 output Tensor
真正流式融合（条件模型）：逐个读 a[i],b[i] → 寄存器临时值 → 写 output[i]
```

`FusionDecision` 证明当前元数据与 guard 下允许这项图改写；reference 相等检查有限输入的函数结果。它们均没有证明执行器消除了完整中间张量。当前 `_execute_ops` 的 fused 分支仍调用 `_elementwise` 构造 `intermediate`，然后另建 ReLU `Tensor`。

仅在连续 N 元素、每元素 w 字节、无别名、无额外消费者，并只数裸元素读写时：两算子路径先读 a/b、写 intermediate（3Nw），再读 intermediate、写 output（2Nw），合计 **5Nw**；真正逐元素融合读 a/b、写 output，合计 **3Nw**，差 **2Nw**。N=8、w=4 时为160 B、96 B、64 B。这个条件账不含 Python 对象、分配器、缓存、启动或设备传输；不是当前执行器的内存测量，更不是 GPU 提速证据。读者可检查当前分支是否构造完整 intermediate，再决定能否引用3Nw模型。


## 练习

1. 增加 `mul -> relu` 数值样例，同时检查融合前后 shape 和值，不只检查 op 名。
2. 为一个 producer 增加第二个 consumer，观察 `producer-has-multiple-uses`；再设计需要什么中间值物化策略才能放宽它。
3. 将 `output_alias_group` 改为更精细的 read/write effect 集合，为“可能别名但只读”与“写后再读”分别写测试。
4. 为 guard 失败增加显式 fallback 到 reference graph，并计数 fast-path/fallback；不要把 fallback 次数伪装成性能加速比。

## 成功标准

- 6 个 unittest 全部通过，包含 shape 传播、静态融合数值对照、动态 guard 命中/失配与三类阻断条件。
- 每次融合尝试都有确定的 `FusionDecision`，且缺少动态特化时保留原 op，不默认某个 shape。
- 能解释“元数据合法”、“有限 reference 值相等”和“真实 GPU/kernel 验收”是三个不同证据层。

## 精确伴随文件

<!-- code-sync: ./tensor_lowering.py -->
```python
#!/usr/bin/env python3
"""Pure-Python tensor metadata, guarded fusion, and reference execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


Shape = tuple[int | None, ...]


@dataclass(frozen=True)
class TensorMeta:
    shape: Shape
    layout: str = "contiguous"
    alias_group: str | None = None


@dataclass(frozen=True)
class Op:
    kind: str
    output: str
    inputs: tuple[str, ...]
    has_side_effect: bool = False
    output_alias_group: str | None = None


@dataclass(frozen=True)
class Graph:
    inputs: Mapping[str, TensorMeta]
    ops: tuple[Op, ...]
    outputs: tuple[str, ...]


@dataclass(frozen=True)
class Tensor:
    shape: tuple[int, ...]
    data: tuple[float, ...]

    def __post_init__(self) -> None:
        size = 1
        for dimension in self.shape:
            if dimension <= 0:
                raise ValueError(f"runtime dimensions must be positive: {self.shape}")
            size *= dimension
        if size != len(self.data):
            raise ValueError(f"shape {self.shape} needs {size} values, got {len(self.data)}")


@dataclass(frozen=True)
class ShapeGuard:
    value: str
    expected: tuple[int, ...]


@dataclass(frozen=True)
class FusionDecision:
    producer: str
    consumer: str
    fused: bool
    reason: str


@dataclass(frozen=True)
class ExecOp:
    kind: str
    output: str
    inputs: tuple[str, ...]


@dataclass(frozen=True)
class LoweredGraph:
    inputs: Mapping[str, TensorMeta]
    ops: tuple[ExecOp, ...]
    outputs: tuple[str, ...]
    guards: tuple[ShapeGuard, ...]
    decisions: tuple[FusionDecision, ...]


class GuardFailure(ValueError):
    pass


def _compatible_shape(left: Shape, right: Shape) -> Shape:
    if len(left) != len(right):
        raise ValueError(f"rank mismatch: {left} vs {right}")
    result: list[int | None] = []
    for left_dim, right_dim in zip(left, right):
        if left_dim is not None and right_dim is not None and left_dim != right_dim:
            raise ValueError(f"shape mismatch: {left} vs {right}")
        result.append(left_dim if left_dim == right_dim else None)
    return tuple(result)


def infer_metadata(graph: Graph) -> dict[str, TensorMeta]:
    """Propagate shape/layout/alias metadata in topological order."""
    values = dict(graph.inputs)
    for op in graph.ops:
        if op.output in values:
            raise ValueError(f"value is defined twice: {op.output}")
        try:
            arguments = [values[name] for name in op.inputs]
        except KeyError as error:
            raise ValueError(f"unknown input for {op.output}: {error.args[0]}") from None
        if op.kind in {"add", "mul"}:
            if len(arguments) != 2:
                raise ValueError(f"{op.kind} expects two inputs")
            shape = _compatible_shape(arguments[0].shape, arguments[1].shape)
        elif op.kind == "relu":
            if len(arguments) != 1:
                raise ValueError("relu expects one input")
            shape = arguments[0].shape
        else:
            raise ValueError(f"unsupported op: {op.kind}")
        layout = "contiguous" if all(item.layout == "contiguous" for item in arguments) else "strided"
        values[op.output] = TensorMeta(shape, layout, op.output_alias_group)
    for output in graph.outputs:
        if output not in values:
            raise ValueError(f"unknown graph output: {output}")
    return values


def _validate_specialization(meta: TensorMeta, concrete: Sequence[int], name: str) -> tuple[int, ...]:
    expected = tuple(concrete)
    if len(expected) != len(meta.shape) or any(dimension <= 0 for dimension in expected):
        raise ValueError(f"invalid specialization for {name}: {expected}")
    for declared, actual in zip(meta.shape, expected):
        if declared is not None and declared != actual:
            raise ValueError(f"specialization contradicts {name}: {meta.shape} vs {expected}")
    return expected


def _plan_pair(
    graph: Graph,
    metadata: Mapping[str, TensorMeta],
    index: int,
    specializations: Mapping[str, Sequence[int]],
) -> tuple[FusionDecision, tuple[ShapeGuard, ...]]:
    producer = graph.ops[index]
    consumer = graph.ops[index + 1]
    base = (producer.output, consumer.output)
    if (producer.kind, consumer.kind) not in {("add", "relu"), ("mul", "relu")}:
        return FusionDecision(*base, False, "unsupported-pattern"), ()
    if consumer.inputs != (producer.output,):
        return FusionDecision(*base, False, "not-a-direct-chain"), ()
    uses = sum(producer.output in op.inputs for op in graph.ops[index + 1 :])
    uses += producer.output in graph.outputs
    if uses != 1:
        return FusionDecision(*base, False, "producer-has-multiple-uses"), ()
    if producer.has_side_effect or consumer.has_side_effect:
        return FusionDecision(*base, False, "side-effect-barrier"), ()
    involved = [metadata[name] for name in producer.inputs]
    involved.extend((metadata[producer.output], metadata[consumer.output]))
    if any(item.layout != "contiguous" for item in involved):
        return FusionDecision(*base, False, "layout-not-contiguous"), ()
    if producer.output_alias_group is not None or consumer.output_alias_group is not None:
        return FusionDecision(*base, False, "alias-not-proven-independent"), ()

    guards: list[ShapeGuard] = []
    for name in producer.inputs:
        meta = metadata[name]
        if None not in meta.shape:
            continue
        if name not in graph.inputs:
            return FusionDecision(*base, False, "dynamic-intermediate-needs-guard"), ()
        if name not in specializations:
            return FusionDecision(*base, False, "dynamic-shape-needs-guard"), ()
        guards.append(ShapeGuard(name, _validate_specialization(meta, specializations[name], name)))
    return FusionDecision(*base, True, "legal"), tuple(guards)


def lower_graph(
    graph: Graph,
    specializations: Mapping[str, Sequence[int]] | None = None,
) -> LoweredGraph:
    """Fuse adjacent elementwise chains only when metadata proves legality."""
    metadata = infer_metadata(graph)
    concrete = specializations or {}
    lowered: list[ExecOp] = []
    decisions: list[FusionDecision] = []
    guards: list[ShapeGuard] = []
    index = 0
    while index < len(graph.ops):
        if index + 1 < len(graph.ops):
            decision, pair_guards = _plan_pair(graph, metadata, index, concrete)
            decisions.append(decision)
            if decision.fused:
                producer, consumer = graph.ops[index : index + 2]
                lowered.append(ExecOp(f"fused_{producer.kind}_relu", consumer.output, producer.inputs))
                guards.extend(pair_guards)
                index += 2
                continue
        op = graph.ops[index]
        lowered.append(ExecOp(op.kind, op.output, op.inputs))
        index += 1
    unique_guards = {(guard.value, guard.expected): guard for guard in guards}
    return LoweredGraph(
        graph.inputs,
        tuple(lowered),
        graph.outputs,
        tuple(unique_guards[key] for key in sorted(unique_guards)),
        tuple(decisions),
    )


def _check_feed(name: str, meta: TensorMeta, tensor: Tensor) -> None:
    if len(meta.shape) != len(tensor.shape):
        raise ValueError(f"feed rank mismatch for {name}: {meta.shape} vs {tensor.shape}")
    for declared, actual in zip(meta.shape, tensor.shape):
        if declared is not None and declared != actual:
            raise ValueError(f"feed shape mismatch for {name}: {meta.shape} vs {tensor.shape}")


def _elementwise(kind: str, left: Tensor, right: Tensor) -> Tensor:
    if left.shape != right.shape:
        raise ValueError(f"runtime elementwise shape mismatch: {left.shape} vs {right.shape}")
    if kind == "add":
        data = tuple(a + b for a, b in zip(left.data, right.data))
    elif kind == "mul":
        data = tuple(a * b for a, b in zip(left.data, right.data))
    else:
        raise ValueError(f"not an elementwise binary op: {kind}")
    return Tensor(left.shape, data)


def _execute_ops(
    inputs: Mapping[str, TensorMeta],
    ops: Sequence[ExecOp],
    outputs: Sequence[str],
    feeds: Mapping[str, Tensor],
) -> tuple[Tensor, ...]:
    if set(feeds) != set(inputs):
        raise ValueError(f"feeds must be exactly {sorted(inputs)}")
    values = dict(feeds)
    for name, meta in inputs.items():
        _check_feed(name, meta, values[name])
    for op in ops:
        arguments = [values[name] for name in op.inputs]
        if op.kind in {"add", "mul"}:
            result = _elementwise(op.kind, arguments[0], arguments[1])
        elif op.kind == "relu":
            source = arguments[0]
            result = Tensor(source.shape, tuple(max(0.0, value) for value in source.data))
        elif op.kind in {"fused_add_relu", "fused_mul_relu"}:
            binary_kind = op.kind.removeprefix("fused_").removesuffix("_relu")
            intermediate = _elementwise(binary_kind, arguments[0], arguments[1])
            result = Tensor(intermediate.shape, tuple(max(0.0, value) for value in intermediate.data))
        else:
            raise ValueError(f"unsupported execution op: {op.kind}")
        values[op.output] = result
    return tuple(values[name] for name in outputs)


def run_reference(graph: Graph, feeds: Mapping[str, Tensor]) -> tuple[Tensor, ...]:
    infer_metadata(graph)
    ops = tuple(ExecOp(op.kind, op.output, op.inputs) for op in graph.ops)
    return _execute_ops(graph.inputs, ops, graph.outputs, feeds)


def run_lowered(lowered: LoweredGraph, feeds: Mapping[str, Tensor]) -> tuple[Tensor, ...]:
    for guard in lowered.guards:
        if guard.value not in feeds or feeds[guard.value].shape != guard.expected:
            actual = feeds[guard.value].shape if guard.value in feeds else None
            raise GuardFailure(f"shape guard failed for {guard.value}: expected {guard.expected}, got {actual}")
    return _execute_ops(lowered.inputs, lowered.ops, lowered.outputs, feeds)


def demo_graph() -> Graph:
    dynamic = TensorMeta((None, 4))
    return Graph(
        {"x": dynamic, "bias": dynamic},
        (Op("add", "sum", ("x", "bias")), Op("relu", "out", ("sum",))),
        ("out",),
    )


def main() -> None:
    graph = demo_graph()
    lowered = lower_graph(graph, {"x": (2, 4), "bias": (2, 4)})
    feeds = {
        "x": Tensor((2, 4), (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)),
        "bias": Tensor((2, 4), (1.0,) * 8),
    }
    print(f"metadata={infer_metadata(graph)}")
    print(f"decisions={lowered.decisions}")
    print(f"guards={lowered.guards}")
    print(f"reference={run_reference(graph, feeds)}")
    print(f"lowered={run_lowered(lowered, feeds)}")


if __name__ == "__main__":
    main()
```

<!-- code-sync: ./test_tensor_lowering.py -->
```python
import unittest

from tensor_lowering import (
    Graph,
    GuardFailure,
    Op,
    Tensor,
    TensorMeta,
    infer_metadata,
    lower_graph,
    run_lowered,
    run_reference,
)


def two_op_graph(
    shape: tuple[int | None, ...] = (2, 2),
    *,
    layout: str = "contiguous",
    output_alias_group: str | None = None,
    side_effect: bool = False,
) -> Graph:
    meta = TensorMeta(shape, layout)
    return Graph(
        {"x": meta, "y": meta},
        (
            Op("add", "sum", ("x", "y"), side_effect, output_alias_group),
            Op("relu", "out", ("sum",)),
        ),
        ("out",),
    )


class MetadataTests(unittest.TestCase):
    def test_shape_propagation_preserves_dynamic_dimension(self) -> None:
        metadata = infer_metadata(two_op_graph((None, 4)))
        self.assertEqual(metadata["sum"].shape, (None, 4))
        self.assertEqual(metadata["out"].shape, (None, 4))

    def test_incompatible_static_shapes_are_rejected(self) -> None:
        graph = Graph(
            {"x": TensorMeta((2, 4)), "y": TensorMeta((3, 4))},
            (Op("add", "out", ("x", "y")),),
            ("out",),
        )
        with self.assertRaisesRegex(ValueError, r"shape mismatch: \(2, 4\) vs \(3, 4\)"):
            infer_metadata(graph)


class FusionTests(unittest.TestCase):
    def test_static_fusion_matches_reference_values(self) -> None:
        graph = two_op_graph()
        lowered = lower_graph(graph)
        feeds = {
            "x": Tensor((2, 2), (-4.0, 2.0, 3.0, -1.0)),
            "y": Tensor((2, 2), (1.0, 1.0, -5.0, 4.0)),
        }
        self.assertEqual([op.kind for op in lowered.ops], ["fused_add_relu"])
        self.assertEqual(run_lowered(lowered, feeds), run_reference(graph, feeds))
        self.assertEqual(run_lowered(lowered, feeds)[0].data, (0.0, 3.0, 0.0, 3.0))

    def test_dynamic_specialization_emits_and_checks_guards(self) -> None:
        graph = two_op_graph((None, 4))
        lowered = lower_graph(graph, {"x": (2, 4), "y": (2, 4)})
        self.assertEqual(
            [(guard.value, guard.expected) for guard in lowered.guards],
            [("x", (2, 4)), ("y", (2, 4))],
        )
        bad_feeds = {
            "x": Tensor((3, 4), (1.0,) * 12),
            "y": Tensor((3, 4), (1.0,) * 12),
        }
        with self.assertRaisesRegex(
            GuardFailure,
            r"shape guard failed for x: expected \(2, 4\), got \(3, 4\)",
        ):
            run_lowered(lowered, bad_feeds)

    def test_dynamic_shape_without_specialization_stays_unfused(self) -> None:
        lowered = lower_graph(two_op_graph((None, 4)))
        self.assertEqual([op.kind for op in lowered.ops], ["add", "relu"])
        self.assertEqual(lowered.decisions[0].reason, "dynamic-shape-needs-guard")

    def test_layout_alias_and_side_effect_each_block_fusion(self) -> None:
        cases = (
            (two_op_graph(layout="strided"), "layout-not-contiguous"),
            (two_op_graph(output_alias_group="buffer-x"), "alias-not-proven-independent"),
            (two_op_graph(side_effect=True), "side-effect-barrier"),
        )
        for graph, reason in cases:
            with self.subTest(reason=reason):
                lowered = lower_graph(graph)
                self.assertEqual([op.kind for op in lowered.ops], ["add", "relu"])
                self.assertEqual(lowered.decisions[0].reason, reason)


if __name__ == "__main__":
    unittest.main()
```

---

**上一站**：[[计算机知识/80-实践/08-编译原理/07-LLVM与MLIR工具链探针/README|LLVM 与 MLIR 工具链探针]] · **下一站**：[[计算机知识/80-实践/08-编译原理/09-MiniLang端到端编译器/README|MiniLang 端到端编译器]] · **返回**：[[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践 MOC]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
