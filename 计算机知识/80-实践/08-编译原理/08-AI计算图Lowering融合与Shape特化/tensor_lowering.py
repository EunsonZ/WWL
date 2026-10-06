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
