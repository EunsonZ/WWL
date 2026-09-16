"""带 verifier 和可观察专用化/guard 回退的教学 operand-stack VM。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class Instruction:
    op: str
    arg: int | None = None


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    pc: int
    detail: str


class VerificationError(ValueError):
    pass


STACK_EFFECT = {
    "LOAD_CONST": 1,
    "LOAD_ARG": 1,
    "ADD_GENERIC": -1,
    "ADD_INT": -1,
    "JUMP": 0,
    "JUMP_IF_FALSE": -1,
    "RETURN": -1,
}


def _require_index(value: int | None, upper_bound: int, description: str) -> None:
    if type(value) is not int or not 0 <= value < upper_bound:
        raise VerificationError(f"invalid {description}: {value!r}")


def verify(code: Sequence[Instruction], constants: Sequence[Any], argument_count: int) -> dict[int, int]:
    """验证操作数、跳转目标、栈下溢、汇合栈深与所有可达路径的终止。"""
    if not code:
        raise VerificationError("empty bytecode")
    for instruction in code:
        if instruction.op not in STACK_EFFECT:
            raise VerificationError(f"unknown opcode: {instruction.op}")
        if instruction.op == "LOAD_CONST":
            _require_index(instruction.arg, len(constants), "constant index")
        elif instruction.op == "LOAD_ARG":
            _require_index(instruction.arg, argument_count, "argument index")
        elif instruction.op in {"JUMP", "JUMP_IF_FALSE"}:
            _require_index(instruction.arg, len(code), "jump target")
        elif instruction.arg is not None:
            raise VerificationError(f"{instruction.op} takes no operand")

    depths: dict[int, int] = {0: 0}
    queue = deque([0])
    terminal_seen = False
    while queue:
        pc = queue.popleft()
        instruction = code[pc]
        depth = depths[pc]
        required = 2 if instruction.op in {"ADD_GENERIC", "ADD_INT"} else (1 if instruction.op in {"JUMP_IF_FALSE", "RETURN"} else 0)
        if depth < required:
            raise VerificationError(f"stack underflow at pc={pc}")
        next_depth = depth + STACK_EFFECT[instruction.op]
        if instruction.op == "RETURN":
            terminal_seen = True
            continue
        if instruction.op == "JUMP":
            targets = (instruction.arg,)
        elif instruction.op == "JUMP_IF_FALSE":
            if pc + 1 >= len(code):
                raise VerificationError(f"conditional fallthrough exits code at pc={pc}")
            targets = (instruction.arg, pc + 1)
        else:
            if pc + 1 >= len(code):
                raise VerificationError(f"reachable path falls off code at pc={pc}")
            targets = (pc + 1,)
        for target in targets:
            assert target is not None
            if target in depths and depths[target] != next_depth:
                raise VerificationError(
                    f"inconsistent stack depth at pc={target}: {depths[target]} vs {next_depth}"
                )
            if target not in depths:
                depths[target] = next_depth
                queue.append(target)
    if not terminal_seen:
        raise VerificationError("no reachable RETURN")
    return depths


class BytecodeVM:
    """解释字节码；这里的“JIT”只改写字节码，不生成机器码。"""

    def __init__(
        self,
        code: Sequence[Instruction],
        constants: Sequence[Any] = (),
        *,
        argument_count: int = 0,
        specialization_threshold: int = 3,
    ) -> None:
        if specialization_threshold < 1:
            raise ValueError("specialization_threshold must be positive")
        verify(code, constants, argument_count)
        self.code = list(code)
        self.constants = tuple(constants)
        self.argument_count = argument_count
        self.specialization_threshold = specialization_threshold
        self.hotness: dict[int, int] = {}
        self.trace: list[TraceEvent] = []

    def _event(self, kind: str, pc: int, detail: str) -> None:
        self.trace.append(TraceEvent(kind, pc, detail))

    @staticmethod
    def _generic_add(left: Any, right: Any) -> Any:
        return left + right

    def run(self, arguments: Sequence[Any] = (), *, step_limit: int = 10_000) -> Any:
        if len(arguments) != self.argument_count:
            raise ValueError(f"expected {self.argument_count} arguments, got {len(arguments)}")
        stack: list[Any] = []
        pc = 0
        steps = 0
        while True:
            steps += 1
            if steps > step_limit:
                raise RuntimeError("step limit exceeded")
            instruction = self.code[pc]
            op = instruction.op
            if op == "LOAD_CONST":
                stack.append(self.constants[instruction.arg])  # type: ignore[index]
            elif op == "LOAD_ARG":
                stack.append(arguments[instruction.arg])  # type: ignore[index]
            elif op == "ADD_GENERIC":
                right, left = stack.pop(), stack.pop()
                result = self._generic_add(left, right)
                stack.append(result)
                if type(left) is int and type(right) is int:
                    count = self.hotness.get(pc, 0) + 1
                    self.hotness[pc] = count
                    self._event("hotness", pc, f"exact-int observations={count}")
                    if count >= self.specialization_threshold:
                        self.code[pc] = Instruction("ADD_INT")
                        self._event("specialize", pc, "ADD_GENERIC -> ADD_INT bytecode rewrite")
            elif op == "ADD_INT":
                right, left = stack.pop(), stack.pop()
                if type(left) is int and type(right) is int:
                    stack.append(left + right)
                    self._event("guard_hit", pc, "exact int pair")
                else:
                    self._event(
                        "guard_fail",
                        pc,
                        f"{type(left).__name__}+{type(right).__name__}",
                    )
                    stack.append(self._generic_add(left, right))
                    self._event("generic_fallback", pc, "executed generic add; specialization retained")
            elif op == "JUMP":
                pc = instruction.arg  # type: ignore[assignment]
                continue
            elif op == "JUMP_IF_FALSE":
                condition = stack.pop()
                if not condition:
                    pc = instruction.arg  # type: ignore[assignment]
                    continue
            elif op == "RETURN":
                return stack.pop()
            else:  # verify() makes this unreachable unless code is mutated externally.
                raise RuntimeError(f"invalid opcode at runtime: {op}")
            pc += 1


def add_program() -> list[Instruction]:
    return [Instruction("LOAD_ARG", 0), Instruction("LOAD_ARG", 1), Instruction("ADD_GENERIC"), Instruction("RETURN")]


if __name__ == "__main__":
    vm = BytecodeVM(add_program(), argument_count=2, specialization_threshold=2)
    print("run 1:", vm.run((20, 22)))
    print("run 2:", vm.run((40, 2)))
    print("run 3 (guard failure -> generic path):", vm.run(("hot", " path")))
    print("trace:")
    for event in vm.trace:
        print(f"  pc={event.pc} {event.kind}: {event.detail}")
    print("boundary: specialized bytecode only; no native machine code was generated")
