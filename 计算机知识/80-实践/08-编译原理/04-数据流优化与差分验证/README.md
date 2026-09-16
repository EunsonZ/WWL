---
type: lab
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 60
domain: computer-science
topics:
  - compiler
  - dataflow-analysis
  - optimization
  - differential-testing
tags:
  - computer-science/compiler/lab
---

# 数据流优化与差分验证

## 目标

亲手观察一个有限数据流格怎样通过工作列表到达不动点，再把分析事实用于常量传播、常量分支裁剪和活跃性 DCE。最后用同一个解释器分别执行优化前后程序，以固定 seed 的有限输入寻找语义差异。

先读：[[计算机知识/70-编译原理/09-数据流分析格不动点活跃性与到达定义|数据流分析：格、不动点、活跃性与到达定义]]、[[计算机知识/70-编译原理/10-优化Pass别名分析与阶段排序|优化 Pass、别名分析与阶段排序]]、[[计算机知识/70-编译原理/11-优化正确性语义保持与验证测试|优化正确性、语义保持与验证测试]]。返回 [[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]。

## 安全与证据边界

- 脚本只解释代码中构造的教学 IR，不解析、不导入也不执行外部或不可信代码；仅使用 Python 标准库。
- 常量域只容纳 `[-128, 127]`，加上 `UNDEF` 与 `OVERDEFINED` 后是一个有限的平坦格；超出范围的分析结果保守提升为 `OVERDEFINED`。解释器仍借用 Python 整数语义，不代表生产编译器的溢出、异常、别名与内存模型。
- `differential_check` 的固定 seed 使一次实验可复现，但 100 个或任意有限个样例都不是等价性证明。它只能找到反例，不能证明所有输入上正确。
- unittest 证明这里列出的有限行为通过；没有证明算法对任意 IR、真实语言或真实优化流水线正确。

## 运行

在本目录执行：

```bash
python3 dataflow_opt.py
python3 -m unittest -v test_dataflow_opt.py
```

## 观察

示例中的 `two + three` 折叠为 `5`，`five - five` 折叠为 `0`，条件跳转因此成为无条件跳转；不可达的 `out = 999` 与不活跃的 `dead = 77` 消失。输出还报告工作列表访问次数，以及 `seed=20260904` 下 100 个优化前后相同的有限观测。

特别留意：分析状态是“某条指令执行前”的事实；DCE 则反向计算“某定义之后是否仍被使用”。两个方向不同，却都在有限格上单调迭代。

## 练习

1. 把 `demo_program()` 中的常量分支改成取决于输入，解释为什么它不能被裁剪。
2. 给 IR 增加除法。先明确除零和整数舍入语义，再写测试；不要只加一行运算表。
3. 故意把优化后的乘数从 `five` 改成 `two`，观察差分检查给出的第一个反例；随后恢复文件。
4. 增加穷举 `x ∈ [-10, 10]` 的检查，并解释它为什么仍不是全输入证明。

## 成功标准

- 5 个 unittest 全部通过。
- demo 输出包含折叠后的 `five = const 5` 与 `jump zero`，不再包含两条已删除定义。
- 两次使用相同 seed 和 case 数得到完全相同的输入、优化前结果、优化后结果三元组。
- 能明确说出“工作列表达到此有限抽象域的不动点”和“程序在所有输入上语义等价”不是同一结论。

## 完整源码

<!-- code-sync: ./dataflow_opt.py -->
```python
"""有限格上的常量传播、活跃性 DCE 与有限差分验证教学实现。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
import random
from typing import Iterable, Mapping, Sequence


class Kind(Enum):
    UNDEF = auto()
    CONSTANT = auto()
    OVERDEFINED = auto()


@dataclass(frozen=True)
class Value:
    kind: Kind
    number: int | None = None

    def __str__(self) -> str:
        if self.kind is Kind.CONSTANT:
            return str(self.number)
        return self.kind.name


UNDEF = Value(Kind.UNDEF)
OVERDEFINED = Value(Kind.OVERDEFINED)
MIN_CONSTANT = -128
MAX_CONSTANT = 127


def constant(number: int) -> Value:
    if MIN_CONSTANT <= number <= MAX_CONSTANT:
        return Value(Kind.CONSTANT, number)
    return OVERDEFINED


def join(left: Value, right: Value) -> Value:
    """返回三点常量格上的最小上界。"""
    if left == right:
        return left
    if left.kind is Kind.UNDEF:
        return right
    if right.kind is Kind.UNDEF:
        return left
    return OVERDEFINED


@dataclass(frozen=True)
class Instruction:
    op: str
    dst: str | None = None
    args: tuple[str | int, ...] = ()

    def text(self) -> str:
        tail = ", ".join(map(str, self.args))
        if self.dst is not None:
            return f"{self.dst} = {self.op.lower()} {tail}".rstrip()
        return f"{self.op.lower()} {tail}".rstrip()


PURE_DEFINITIONS = {"CONST", "COPY", "ADD", "SUB", "MUL"}


def label_positions(program: Sequence[Instruction]) -> dict[str, int]:
    labels: dict[str, int] = {}
    for index, instruction in enumerate(program):
        if instruction.op == "LABEL":
            name = str(instruction.args[0])
            if name in labels:
                raise ValueError(f"duplicate label: {name}")
            labels[name] = index
    return labels


def successors(program: Sequence[Instruction]) -> list[tuple[int, ...]]:
    labels = label_positions(program)
    result: list[tuple[int, ...]] = []
    for index, instruction in enumerate(program):
        fallthrough = (index + 1,) if index + 1 < len(program) else ()
        if instruction.op == "JUMP":
            result.append((labels[str(instruction.args[0])],))
        elif instruction.op == "JZ":
            target = labels[str(instruction.args[1])]
            result.append(tuple(dict.fromkeys((target, *fallthrough))))
        elif instruction.op == "RETURN":
            result.append(())
        else:
            result.append(fallthrough)
    return result


def variables(program: Sequence[Instruction]) -> set[str]:
    names = {instruction.dst for instruction in program if instruction.dst}
    for instruction in program:
        names.update(uses(instruction))
    return names


def uses(instruction: Instruction) -> set[str]:
    if instruction.op in {"COPY", "RETURN"}:
        return {str(instruction.args[0])}
    if instruction.op in {"ADD", "SUB", "MUL"}:
        return {str(instruction.args[0]), str(instruction.args[1])}
    if instruction.op == "JZ":
        return {str(instruction.args[0])}
    return set()


def merge_states(states: Iterable[Mapping[str, Value]], names: set[str]) -> dict[str, Value]:
    iterator = iter(states)
    try:
        first = next(iterator)
    except StopIteration:
        return {}
    merged = {name: first.get(name, UNDEF) for name in names}
    for state in iterator:
        merged = {name: join(merged.get(name, UNDEF), state.get(name, UNDEF)) for name in names}
    return {name: value for name, value in merged.items() if value.kind is not Kind.UNDEF}


def evaluate_binary(op: str, left: Value, right: Value) -> Value:
    if left.kind is Kind.OVERDEFINED or right.kind is Kind.OVERDEFINED:
        return OVERDEFINED
    if left.kind is Kind.UNDEF or right.kind is Kind.UNDEF:
        return UNDEF
    operations = {"ADD": int.__add__, "SUB": int.__sub__, "MUL": int.__mul__}
    return constant(operations[op](left.number, right.number))  # type: ignore[arg-type]


def transfer(instruction: Instruction, state: Mapping[str, Value]) -> dict[str, Value]:
    output = dict(state)
    if instruction.op == "CONST":
        output[instruction.dst or ""] = constant(int(instruction.args[0]))
    elif instruction.op == "INPUT":
        output[instruction.dst or ""] = OVERDEFINED
    elif instruction.op == "COPY":
        output[instruction.dst or ""] = state.get(str(instruction.args[0]), UNDEF)
    elif instruction.op in {"ADD", "SUB", "MUL"}:
        left = state.get(str(instruction.args[0]), UNDEF)
        right = state.get(str(instruction.args[1]), UNDEF)
        output[instruction.dst or ""] = evaluate_binary(instruction.op, left, right)
    return output


@dataclass(frozen=True)
class Analysis:
    in_states: tuple[dict[str, Value] | None, ...]
    out_states: tuple[dict[str, Value] | None, ...]
    visits: int


def constant_propagation(program: Sequence[Instruction]) -> Analysis:
    """用工作列表求前向不动点；None 表示尚不可达。"""
    if not program:
        return Analysis((), (), 0)
    edges = successors(program)
    predecessors: list[list[int]] = [[] for _ in program]
    for source, targets in enumerate(edges):
        for target in targets:
            predecessors[target].append(source)
    names = variables(program)
    in_states: list[dict[str, Value] | None] = [None for _ in program]
    out_states: list[dict[str, Value] | None] = [None for _ in program]
    in_states[0] = {}
    queue = deque([0])
    queued = {0}
    visits = 0
    while queue:
        index = queue.popleft()
        queued.remove(index)
        visits += 1
        incoming = [out_states[p] for p in predecessors[index] if out_states[p] is not None]
        new_input = merge_states(incoming, names) if incoming else ({} if index == 0 else None)
        if new_input is None:
            continue
        new_output = transfer(program[index], new_input)
        changed = new_input != in_states[index] or new_output != out_states[index]
        in_states[index] = new_input
        out_states[index] = new_output
        if changed:
            for target in edges[index]:
                if target not in queued:
                    queue.append(target)
                    queued.add(target)
    return Analysis(tuple(in_states), tuple(out_states), visits)


def rewrite_constants(program: Sequence[Instruction], analysis: Analysis) -> list[Instruction]:
    rewritten: list[Instruction] = []
    for index, instruction in enumerate(program):
        state = analysis.in_states[index]
        if state is None:
            rewritten.append(instruction)
            continue
        if instruction.op in {"COPY", "ADD", "SUB", "MUL"}:
            output = transfer(instruction, state).get(instruction.dst or "", UNDEF)
            if output.kind is Kind.CONSTANT:
                rewritten.append(Instruction("CONST", instruction.dst, (output.number,)))
                continue
        if instruction.op == "JZ":
            condition = state.get(str(instruction.args[0]), UNDEF)
            if condition.kind is Kind.CONSTANT:
                rewritten.append(Instruction("JUMP", args=(instruction.args[1],)) if condition.number == 0 else Instruction("NOP"))
                continue
        rewritten.append(instruction)
    return rewritten


def remove_unreachable(program: Sequence[Instruction]) -> list[Instruction]:
    if not program:
        return []
    edges = successors(program)
    reachable = {0}
    queue = deque([0])
    while queue:
        for target in edges[queue.popleft()]:
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    return [instruction for index, instruction in enumerate(program) if index in reachable]


def eliminate_dead_definitions(program: Sequence[Instruction]) -> list[Instruction]:
    """用有限幂集格上的反向活跃性分析删除无副作用死定义。"""
    if not program:
        return []
    edges = successors(program)
    live_in = [set() for _ in program]
    live_out = [set() for _ in program]
    queue = deque(range(len(program) - 1, -1, -1))
    predecessors = [[] for _ in program]
    for source, targets in enumerate(edges):
        for target in targets:
            predecessors[target].append(source)
    while queue:
        index = queue.popleft()
        new_out = set().union(*(live_in[target] for target in edges[index])) if edges[index] else set()
        instruction = program[index]
        new_in = uses(instruction) | (new_out - ({instruction.dst} if instruction.dst else set()))
        if new_in != live_in[index] or new_out != live_out[index]:
            live_in[index], live_out[index] = new_in, new_out
            queue.extend(predecessors[index])
    return [
        instruction
        for index, instruction in enumerate(program)
        if not (instruction.op in PURE_DEFINITIONS and instruction.dst not in live_out[index])
    ]


def optimize(program: Sequence[Instruction]) -> tuple[list[Instruction], Analysis]:
    analysis = constant_propagation(program)
    rewritten = rewrite_constants(program, analysis)
    reachable = remove_unreachable(rewritten)
    return eliminate_dead_definitions(reachable), analysis


def interpret(program: Sequence[Instruction], inputs: Mapping[str, int], step_limit: int = 1_000) -> int:
    labels = label_positions(program)
    values: dict[str, int] = {}
    pc = 0
    steps = 0
    while 0 <= pc < len(program):
        steps += 1
        if steps > step_limit:
            raise RuntimeError("step limit exceeded")
        instruction = program[pc]
        op = instruction.op
        if op == "INPUT":
            values[instruction.dst or ""] = int(inputs[str(instruction.args[0])])
        elif op == "CONST":
            values[instruction.dst or ""] = int(instruction.args[0])
        elif op == "COPY":
            values[instruction.dst or ""] = values[str(instruction.args[0])]
        elif op in {"ADD", "SUB", "MUL"}:
            left, right = (values[str(name)] for name in instruction.args[:2])
            values[instruction.dst or ""] = {"ADD": left + right, "SUB": left - right, "MUL": left * right}[op]
        elif op == "JUMP":
            pc = labels[str(instruction.args[0])]
            continue
        elif op == "JZ" and values[str(instruction.args[0])] == 0:
            pc = labels[str(instruction.args[1])]
            continue
        elif op == "RETURN":
            return values[str(instruction.args[0])]
        elif op not in {"LABEL", "NOP", "JZ"}:
            raise ValueError(f"unknown operation: {op}")
        pc += 1
    raise RuntimeError("program terminated without RETURN")


def differential_check(
    original: Sequence[Instruction],
    optimized: Sequence[Instruction],
    *,
    seed: int = 20260904,
    cases: int = 100,
) -> list[tuple[int, int, int]]:
    """在固定伪随机样例上比对结果；有限样例不是等价性证明。"""
    generator = random.Random(seed)
    observations = []
    for _ in range(cases):
        x = generator.randint(-1_000, 1_000)
        before = interpret(original, {"x": x})
        after = interpret(optimized, {"x": x})
        observations.append((x, before, after))
        if before != after:
            raise AssertionError(f"mismatch for x={x}: {before} != {after}")
    return observations


def demo_program() -> list[Instruction]:
    return [
        Instruction("INPUT", "x", ("x",)),
        Instruction("CONST", "two", (2,)),
        Instruction("CONST", "three", (3,)),
        Instruction("ADD", "five", ("two", "three")),
        Instruction("SUB", "condition", ("five", "five")),
        Instruction("JZ", args=("condition", "zero")),
        Instruction("CONST", "out", (999,)),
        Instruction("JUMP", args=("end",)),
        Instruction("LABEL", args=("zero",)),
        Instruction("MUL", "out", ("x", "five")),
        Instruction("CONST", "dead", (77,)),
        Instruction("LABEL", args=("end",)),
        Instruction("RETURN", args=("out",)),
    ]


if __name__ == "__main__":
    before = demo_program()
    after, facts = optimize(before)
    observations = differential_check(before, after)
    print(f"work-list visits: {facts.visits}")
    print("before:")
    print("\n".join(f"  {instruction.text()}" for instruction in before))
    print("after:")
    print("\n".join(f"  {instruction.text()}" for instruction in after))
    print(f"finite differential cases: {len(observations)} (seed=20260904; not a proof)")
```

## 测试

<!-- code-sync: ./test_dataflow_opt.py -->
```python
import unittest

from dataflow_opt import (
    Instruction,
    Kind,
    OVERDEFINED,
    UNDEF,
    constant,
    constant_propagation,
    demo_program,
    differential_check,
    interpret,
    join,
    optimize,
)


class LatticeTests(unittest.TestCase):
    def test_join_is_monotone_for_three_point_constant_lattice(self) -> None:
        self.assertEqual(join(UNDEF, constant(4)), constant(4))
        self.assertEqual(join(constant(4), constant(4)), constant(4))
        self.assertEqual(join(constant(4), constant(5)), OVERDEFINED)
        self.assertEqual(join(constant(4), OVERDEFINED), OVERDEFINED)
        self.assertEqual(constant(128), OVERDEFINED)

    def test_work_list_reaches_loop_fixed_point(self) -> None:
        program = [
            Instruction("CONST", "x", (0,)),
            Instruction("LABEL", args=("loop",)),
            Instruction("ADD", "x", ("x", "one")),
            Instruction("CONST", "one", (1,)),
            Instruction("JUMP", args=("loop",)),
        ]
        analysis = constant_propagation(program)
        self.assertGreater(analysis.visits, len(program))
        self.assertEqual(analysis.in_states[2]["x"].kind, Kind.OVERDEFINED)  # type: ignore[index]


class OptimizationTests(unittest.TestCase):
    def test_constant_folding_branch_pruning_and_dce(self) -> None:
        optimized, _ = optimize(demo_program())
        text = [instruction.text() for instruction in optimized]
        self.assertIn("five = const 5", text)
        self.assertIn("jump zero", text)
        self.assertNotIn("out = const 999", text)
        self.assertNotIn("dead = const 77", text)
        self.assertEqual(interpret(optimized, {"x": -7}), -35)

    def test_fixed_seed_finite_differential_check(self) -> None:
        original = demo_program()
        optimized, _ = optimize(original)
        first = differential_check(original, optimized, seed=1234, cases=64)
        second = differential_check(original, optimized, seed=1234, cases=64)
        self.assertEqual(first, second)
        self.assertTrue(all(before == after for _, before, after in first))

    def test_differential_check_exposes_bad_rewrite(self) -> None:
        bad = [Instruction("CONST", "out", (1,)), Instruction("RETURN", args=("out",))]
        with self.assertRaises(AssertionError):
            differential_check(demo_program(), bad, cases=1)


if __name__ == "__main__":
    unittest.main()
```


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
