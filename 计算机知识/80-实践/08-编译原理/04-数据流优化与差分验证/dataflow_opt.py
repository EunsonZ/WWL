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
