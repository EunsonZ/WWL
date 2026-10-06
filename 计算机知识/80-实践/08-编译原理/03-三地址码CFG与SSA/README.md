---
type: practice
stage: 3
status: ready
difficulty: 进阶
estimated_minutes: 50
domain: computer-science
tags:
  - computer-science/compiler
  - computer-science/cfg
  - computer-science/ssa
---

# MiniLang 三地址码、CFG 与 SSA

本实验将固定的 MiniLang 菱形控制流 if x < 0 { x = -x } else { x = x }; return x + 1 表示为三地址码：basic block 有显式 terminator，CFG 从 terminator 推导 pred/succ，迭代求支配集，再在汇合块为两个 x 定义插入 phi 并重命名为 SSA。验证器检查终止器、唯一 SSA 定义、phi 入边集合与定义对使用/phi 边的支配关系。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/08-编译原理/03-三地址码CFG与SSA"
python3 -m unittest -v
~~~

预期 Ran 10 tests ... OK。观察 join 的前驱恰为 neg、nonneg，但它的支配集不含任一分支；SSA 中 x.3 = phi(neg: x.1, nonneg: x.2)，验证器返回空列表。删除 phi 输入的定义会得到确定的 undefined value 诊断；把同一 block 中的 use 放在定义之前、写错 terminator、给 terminator 少传参数、跳到不存在的 block 或遗留不可达 block，都会得到确定诊断。

安全边界：仅 Python 标准库，内存中构造固定 CFG；不联网、不安装、不写用户文件、不执行或优化任意用户程序。测试可能生成 __pycache__/，可确认路径后移除；Git diff 或编辑器撤销可恢复。范围诚实说明：lowering 与 SSA 构造器只接受四块菱形模板；没有 CFG 构造算法、循环、dominance frontier、通用 phi 插入、内存 SSA、异常边、寄存器分配或机器码生成。验证器的明确合同是：entry 必须存在；每个 block 必须从 entry 可达；jump、branch、return 的 opcode、参数个数和目标块必须合法；普通 use 必须晚于同块定义或由支配块定义；phi 输入则按 predecessor edge 检查。它仍是教学检查器，不是生产级 IR verifier。

练习：构造一个带循环回边的 CFG，先写 pred/succ 与支配集的期望测试；然后以 dominance frontier 为依据扩展通用 phi 插入。成功标准是每个 block 都有 terminator，phi 输入与前驱集合完全一致，且每个 SSA 使用受其定义支配。

相关稳定课：[[计算机知识/30-计算机系统/06-指令系统汇编与程序执行|计算机知识/30-计算机系统/06-指令系统汇编与程序执行]]、[[计算机知识/10-编程语言/02-C++/01-编译链接与CMake|计算机知识/10-编程语言/02-C++/01-编译链接与CMake]]。

<!-- code-sync: ./minilang_ir.py -->
~~~python
"""固定 MiniLang 菱形控制流的 TAC、CFG、支配关系、phi 与 SSA 验证。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instruction:
    op: str
    dest: str | None = None
    args: tuple[object, ...] = ()


@dataclass(frozen=True)
class Terminator:
    op: str
    args: tuple[str, ...]


@dataclass
class Block:
    label: str
    instructions: list[Instruction] = field(default_factory=list)
    terminator: Terminator | None = None


@dataclass
class CFG:
    entry: str
    blocks: dict[str, Block]

    def successors(self, label: str) -> tuple[str, ...]:
        term = self.blocks[label].terminator
        if term is None:
            return ()
        if term.op == "jump" and len(term.args) == 1 and isinstance(term.args[0], str):
            return (term.args[0],)
        if term.op == "branch" and len(term.args) == 3 and all(isinstance(value, str) for value in term.args):
            return term.args[1:]
        return ()

    def predecessors(self, label: str) -> tuple[str, ...]:
        return tuple(candidate for candidate in self.blocks if label in self.successors(candidate))


def lower_diamond_to_tac() -> CFG:
    """下放 `if x < 0 { x = -x } else { x = x }; return x + 1` 的固定教学切片。"""
    return CFG("entry", {
        "entry": Block("entry", [Instruction("param", "x"), Instruction("lt", "c", ("x", 0))], Terminator("branch", ("c", "neg", "nonneg"))),
        "neg": Block("neg", [Instruction("neg", "x", ("x",))], Terminator("jump", ("join",))),
        "nonneg": Block("nonneg", [Instruction("copy", "x", ("x",))], Terminator("jump", ("join",))),
        "join": Block("join", [Instruction("add", "y", ("x", 1))], Terminator("return", ("y",))),
    })


def dominators(cfg: CFG) -> dict[str, set[str]]:
    """经典迭代数据流方程；假定所有块从 entry 可达。"""
    labels = set(cfg.blocks)
    result = {label: ({label} if label == cfg.entry else labels.copy()) for label in labels}
    changed = True
    while changed:
        changed = False
        for label in cfg.blocks:
            if label == cfg.entry:
                continue
            preds = cfg.predecessors(label)
            incoming = set.intersection(*(result[pred] for pred in preds)) if preds else set()
            updated = incoming | {label}
            if updated != result[label]:
                result[label] = updated
                changed = True
    return result


def to_ssa(tac: CFG) -> CFG:
    """为本实验的菱形模板重命名并插入 join 的 phi；不是通用 SSA 构造器。"""
    if set(tac.blocks) != {"entry", "neg", "nonneg", "join"}:
        raise ValueError("this teaching converter accepts the fixed diamond CFG only")
    return CFG("entry", {
        "entry": Block("entry", [Instruction("param", "x.0"), Instruction("lt", "c.0", ("x.0", 0))], Terminator("branch", ("c.0", "neg", "nonneg"))),
        "neg": Block("neg", [Instruction("neg", "x.1", ("x.0",))], Terminator("jump", ("join",))),
        "nonneg": Block("nonneg", [Instruction("copy", "x.2", ("x.0",))], Terminator("jump", ("join",))),
        "join": Block("join", [Instruction("phi", "x.3", (("neg", "x.1"), ("nonneg", "x.2"))), Instruction("add", "y.0", ("x.3", 1))], Terminator("return", ("y.0",))),
    })


def _variables(values: tuple[object, ...]) -> list[str]:
    return [value for value in values if isinstance(value, str) and "." in value]


def _validate_cfg_shape(cfg: CFG) -> list[str]:
    """验证本教学 IR 的控制流契约，并拒绝不可达块。

    `dominators` 的教材实现只处理 entry 可达的 CFG。先在这里验证 entry、
    terminator 与目标块，随后再计算支配关系，避免把不完整图误当成有效 SSA。
    """
    errors: list[str] = []
    if cfg.entry not in cfg.blocks:
        return [f"entry block {cfg.entry} does not exist"]

    for label, block in cfg.blocks.items():
        if block.label != label:
            errors.append(f"{label}: block label does not match mapping key")
        term = block.terminator
        if term is None:
            errors.append(f"{label}: missing terminator")
            continue
        if term.op == "jump":
            if len(term.args) != 1:
                errors.append(f"{label}: jump expects exactly 1 target")
                continue
            targets = term.args
        elif term.op == "branch":
            if len(term.args) != 3:
                errors.append(f"{label}: branch expects condition and exactly 2 targets")
                continue
            condition, *targets = term.args
            if not isinstance(condition, str) or "." not in condition:
                errors.append(f"{label}: branch condition must be an SSA value")
            if targets[0] == targets[1]:
                errors.append(f"{label}: branch targets must be distinct")
        elif term.op == "return":
            if len(term.args) != 1:
                errors.append(f"{label}: return expects exactly 1 value")
            continue
        else:
            errors.append(f"{label}: unknown terminator {term.op}")
            continue

        for target in targets:
            if not isinstance(target, str):
                errors.append(f"{label}: terminator target must be a block label")
            elif target not in cfg.blocks:
                errors.append(f"{label}: target block {target} does not exist")

    if errors:
        return errors

    reachable = {cfg.entry}
    pending = [cfg.entry]
    while pending:
        label = pending.pop()
        for successor in cfg.successors(label):
            if successor not in reachable:
                reachable.add(successor)
                pending.append(successor)
    for label in cfg.blocks:
        if label not in reachable:
            errors.append(f"{label}: unreachable block; verifier requires every block to be reachable from entry")
    return errors


def verify_ssa(cfg: CFG) -> list[str]:
    """验证教学 SSA：CFG 结构、唯一性、定义顺序、phi 边与支配关系。

    普通 use 发生在本 block 的某条指令或 terminator 上，因而同块定义必须严格
    在 use 之前；phi 的每个输入则发生在对应 predecessor edge 上，所以检查该
    定义是否支配 *前驱块*，而不是是否支配 phi 所在的 join 块。
    """
    errors = _validate_cfg_shape(cfg)
    if errors:
        return errors

    definitions: dict[str, tuple[str, int]] = {}
    for label, block in cfg.blocks.items():
        saw_non_phi = False
        for position, instruction in enumerate(block.instructions):
            if instruction.op == "phi":
                if saw_non_phi:
                    errors.append(f"{label}: phi instructions must precede ordinary instructions")
            else:
                saw_non_phi = True
            if instruction.dest and "." in instruction.dest:
                if instruction.dest in definitions:
                    errors.append(f"duplicate definition {instruction.dest}")
                else:
                    definitions[instruction.dest] = (label, position)
    if errors:
        return errors

    dom = dominators(cfg)

    def check_ordinary_use(variable: str, label: str, position: int, context: str) -> None:
        definition = definitions.get(variable)
        if definition is None:
            errors.append(f"undefined value {variable}")
            return
        definition_label, definition_position = definition
        if definition_label == label and definition_position >= position:
            errors.append(f"{variable} used before definition in {label}")
        elif definition_label not in dom[label]:
            errors.append(f"{variable} does not dominate {context} in {label}")

    for label, block in cfg.blocks.items():
        expected_predecessors = set(cfg.predecessors(label))
        for position, instruction in enumerate(block.instructions):
            if instruction.op == "phi":
                incoming = instruction.args
                if not all(isinstance(edge, tuple) and len(edge) == 2 for edge in incoming):
                    errors.append(f"{label}: phi inputs must be (predecessor, value) pairs")
                    continue
                predecessors = [edge[0] for edge in incoming]
                if set(predecessors) != expected_predecessors or len(predecessors) != len(expected_predecessors):
                    errors.append(f"{label}: phi predecessors do not match CFG")
                for predecessor, variable in incoming:
                    if not isinstance(predecessor, str) or not isinstance(variable, str):
                        errors.append(f"{label}: phi inputs must contain string predecessor and value")
                        continue
                    definition = definitions.get(variable)
                    if definition is None:
                        errors.append(f"undefined value {variable}")
                    elif definition[0] not in dom[predecessor]:
                        errors.append(f"{variable} does not dominate phi edge {predecessor}->{label}")
                continue
            for variable in _variables(instruction.args):
                check_ordinary_use(variable, label, position, "use")

        term = block.terminator
        assert term is not None  # _validate_cfg_shape already established this invariant.
        if term.op == "branch":
            check_ordinary_use(term.args[0], label, len(block.instructions), "branch condition")
        elif term.op == "return":
            for variable in _variables(term.args):
                check_ordinary_use(variable, label, len(block.instructions), "return")
    return errors
~~~

<!-- code-sync: ./test_minilang_ir.py -->
~~~python
"""固定菱形 CFG 的结构、支配和 SSA 验证测试。"""

from __future__ import annotations

import unittest

from minilang_ir import Block, CFG, Instruction, Terminator, dominators, lower_diamond_to_tac, to_ssa, verify_ssa


class IRTests(unittest.TestCase):
    def test_tac_blocks_and_edges_have_terminators(self) -> None:
        cfg = lower_diamond_to_tac()
        self.assertEqual(cfg.successors("entry"), ("neg", "nonneg"))
        self.assertEqual(cfg.predecessors("join"), ("neg", "nonneg"))
        self.assertTrue(all(block.terminator is not None for block in cfg.blocks.values()))

    def test_dominators_for_diamond(self) -> None:
        dom = dominators(lower_diamond_to_tac())
        self.assertEqual(dom["entry"], {"entry"})
        self.assertEqual(dom["neg"], {"entry", "neg"})
        self.assertEqual(dom["join"], {"entry", "join"})

    def test_ssa_has_phi_and_verifies(self) -> None:
        ssa = to_ssa(lower_diamond_to_tac())
        phi = ssa.blocks["join"].instructions[0]
        self.assertEqual((phi.op, phi.dest, phi.args), ("phi", "x.3", (("neg", "x.1"), ("nonneg", "x.2"))))
        self.assertEqual(verify_ssa(ssa), [])

    def test_verifier_rejects_missing_phi_predecessor_and_definition(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("jump", ("join",))), "join": Block("join", [Instruction("phi", "x.1", (("entry", "x.0"),))], Terminator("return", ("x.1",)))})
        self.assertEqual(verify_ssa(cfg), ["undefined value x.0"])

    def test_verifier_rejects_same_block_use_before_definition(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [
                Instruction("add", "y.0", ("x.0", 1)),
                Instruction("param", "x.0"),
            ], Terminator("return", ("y.0",))),
        })
        self.assertEqual(verify_ssa(cfg), ["x.0 used before definition in entry"])

    def test_verifier_rejects_undefined_branch_condition(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [], Terminator("branch", ("c.0", "yes", "no"))),
            "yes": Block("yes", [], Terminator("return", ("1",))),
            "no": Block("no", [], Terminator("return", ("0",))),
        })
        self.assertEqual(verify_ssa(cfg), ["undefined value c.0"])

    def test_verifier_rejects_unknown_terminator(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("halt", ()))})
        self.assertEqual(verify_ssa(cfg), ["entry: unknown terminator halt"])

    def test_verifier_rejects_wrong_terminator_arity(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("jump", ()))})
        self.assertEqual(verify_ssa(cfg), ["entry: jump expects exactly 1 target"])

    def test_verifier_rejects_missing_target_block(self) -> None:
        cfg = CFG("entry", {"entry": Block("entry", [], Terminator("jump", ("missing",)))})
        self.assertEqual(verify_ssa(cfg), ["entry: target block missing does not exist"])

    def test_verifier_rejects_unreachable_block_under_its_contract(self) -> None:
        cfg = CFG("entry", {
            "entry": Block("entry", [], Terminator("return", ("0",))),
            "dead": Block("dead", [], Terminator("return", ("0",))),
        })
        self.assertEqual(verify_ssa(cfg), ["dead: unreachable block; verifier requires every block to be reachable from entry"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践 MOC]]。


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
