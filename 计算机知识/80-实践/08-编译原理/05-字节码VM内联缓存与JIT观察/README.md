---
type: lab
stage: 5
status: ready
difficulty: 进阶
estimated_minutes: 55
domain: computer-science
topics:
  - bytecode
  - virtual-machine
  - specialization
  - deoptimization
tags:
  - computer-science/compiler/lab
---

# 字节码 VM、内联缓存与 JIT 观察

## 目标

实现并观察三层机制：bytecode verifier 在执行前拒绝结构错误；operand-stack VM 执行已验证指令；热加法点依据运行反馈把 `ADD_GENERIC` 改写为带 exact-int guard 的 `ADD_INT`，guard 失败时回到通用加法路径并留下 trace。

先读：[[计算机知识/70-编译原理/16-解释器字节码VM-JIT与去优化|解释器、字节码 VM、JIT 与去优化]]。关联：[[计算机知识/70-编译原理/11-优化正确性语义保持与验证测试|优化正确性、语义保持与验证测试]]。返回 [[计算机知识/70-编译原理/00-编译原理-MOC|编译原理 MOC]]。

## 安全与证据边界

- 只执行 Python 源码中显式构造的教学 bytecode；不读取 bytecode 文件，不执行外部或不可信代码，仅使用标准库。
- verifier 检查 opcode/operand、索引与跳转范围、栈下溢、汇合栈深、可达路径落空和可达 `RETURN`，但不是形式化证明器，也不验证真实 Python/JVM/Wasm 格式。
- 本实验所谓“JIT 观察”只是把列表中的教学字节码从 `ADD_GENERIC` 改为 `ADD_INT`。它不生成机器码，不分配可执行内存，不测量真实性能，也不冒充 CPython、V8、JVM 或其他实现。
- guard 失败留下 `guard_fail` 与 `generic_fallback` trace 并执行通用语义；这里保留专用化指令，真实系统可能采取去优化、重编译或缓存状态迁移。

## 运行

在本目录执行：

```bash
python3 bytecode_vm.py
python3 -m unittest -v test_bytecode_vm.py
```

## 观察

前两次 exact-int 加法递增同一 PC 的 hotness，达到阈值后 trace 出现 `specialize`。第三次传入字符串时 `ADD_INT` 的 guard 失败，trace 紧接着出现 `generic_fallback`，结果仍按通用 `+` 得到字符串拼接。step limit 测试则说明“verifier 接受”不等于“程序一定终止”。

## 练习

1. 把专用化阈值改为 3，预测哪一次运行之后 opcode 才改变，再用 trace 核对。
2. 让 guard 失败后把 opcode 改回 `ADD_GENERIC`，为这种去专用化策略补测试。
3. 增加 `MUL_GENERIC/MUL_INT`，先集中定义栈效果，再同时更新 verifier 和 VM。
4. 构造一个两条路径在同一 PC 以不同栈深汇合的程序，解释 verifier 为什么必须拒绝。

## 成功标准

- 6 个 unittest 全部通过。
- verifier 能拒绝坏索引、栈下溢、汇合深度不一致和可达落空。
- trace 能按顺序区分 hotness、specialize、guard hit、guard failure 与 generic fallback。
- 能明确说明该实验没有生成真实机器码，运行次数和 trace 也不是性能提升证据。

## 完整源码

<!-- code-sync: ./bytecode_vm.py -->
```python
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
```

## 测试

<!-- code-sync: ./test_bytecode_vm.py -->
```python
import unittest

from bytecode_vm import BytecodeVM, Instruction, VerificationError, add_program, verify


class VerifierTests(unittest.TestCase):
    def test_valid_branch_has_consistent_stack_depth(self) -> None:
        code = [
            Instruction("LOAD_ARG", 0),
            Instruction("JUMP_IF_FALSE", 4),
            Instruction("LOAD_CONST", 0),
            Instruction("JUMP", 5),
            Instruction("LOAD_CONST", 1),
            Instruction("RETURN"),
        ]
        depths = verify(code, (10, 20), argument_count=1)
        self.assertEqual(depths[5], 1)

    def test_rejects_bad_operand_underflow_and_join(self) -> None:
        with self.assertRaises(VerificationError):
            verify([Instruction("LOAD_CONST", 1), Instruction("RETURN")], (0,), 0)
        with self.assertRaises(VerificationError):
            verify([Instruction("ADD_GENERIC"), Instruction("RETURN")], (), 0)
        inconsistent = [
            Instruction("LOAD_ARG", 0),
            Instruction("JUMP_IF_FALSE", 4),
            Instruction("LOAD_CONST", 0),
            Instruction("JUMP", 4),
            Instruction("RETURN"),
        ]
        with self.assertRaises(VerificationError):
            verify(inconsistent, (1,), 1)

    def test_rejects_reachable_fallthrough(self) -> None:
        with self.assertRaises(VerificationError):
            verify([Instruction("LOAD_CONST", 0)], (1,), 0)


class VMTests(unittest.TestCase):
    def test_hot_exact_int_site_specializes(self) -> None:
        vm = BytecodeVM(add_program(), argument_count=2, specialization_threshold=2)
        self.assertEqual(vm.run((20, 22)), 42)
        self.assertEqual(vm.run((40, 2)), 42)
        self.assertEqual(vm.code[2].op, "ADD_INT")
        self.assertIn("specialize", [event.kind for event in vm.trace])
        self.assertEqual(vm.run((1, 2)), 3)
        self.assertIn("guard_hit", [event.kind for event in vm.trace])

    def test_guard_failure_uses_generic_path(self) -> None:
        vm = BytecodeVM(add_program(), argument_count=2, specialization_threshold=1)
        self.assertEqual(vm.run((1, 2)), 3)
        self.assertEqual(vm.run(("byte", "code")), "bytecode")
        kinds = [event.kind for event in vm.trace]
        self.assertIn("guard_fail", kinds)
        self.assertIn("generic_fallback", kinds)
        self.assertEqual(vm.code[2].op, "ADD_INT")

    def test_step_limit_contains_infinite_loop(self) -> None:
        vm = BytecodeVM(
            [
                Instruction("LOAD_ARG", 0),
                Instruction("JUMP_IF_FALSE", 0),
                Instruction("LOAD_CONST", 0),
                Instruction("RETURN"),
            ],
            (1,),
            argument_count=1,
            specialization_threshold=1,
        )
        with self.assertRaises(RuntimeError):
            vm.run((False,), step_limit=5)


if __name__ == "__main__":
    unittest.main()
```



<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/20-数据流优化正确性与编译知识全景|编译原理深化：数据流、不动点和优化正确性]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
