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
                    if predecessor not in expected_predecessors:
                        # The predecessor-set diagnostic above already rejects this edge.
                        # It has no CFG dominance relation to check.
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
