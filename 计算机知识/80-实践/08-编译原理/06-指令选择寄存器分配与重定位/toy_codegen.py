"""Toy ISA 的指令选择、线性扫描分配、spill/reload 与重定位。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class IRInstruction:
    op: str
    dst: str | None = None
    args: tuple[str, ...] = ()
    immediate: int | None = None


@dataclass(frozen=True)
class VirtualInstruction:
    op: str
    dst: str | None = None
    srcs: tuple[str, ...] = ()
    immediate: int | None = None


def select_instructions(program: Sequence[IRInstruction]) -> list[VirtualInstruction]:
    """把极小 SSA 风格 IR 选择为仍使用虚拟寄存器的 Toy ISA。"""
    selected: list[VirtualInstruction] = []
    defined: set[str] = set()
    for instruction in program:
        if any(source not in defined for source in instruction.args):
            missing = [source for source in instruction.args if source not in defined]
            raise ValueError(f"use before definition: {missing}")
        if instruction.op == "const" and instruction.dst and instruction.immediate is not None:
            selected.append(VirtualInstruction("LI", instruction.dst, immediate=instruction.immediate))
        elif instruction.op in {"add", "mul"} and instruction.dst and len(instruction.args) == 2:
            selected.append(VirtualInstruction(instruction.op.upper(), instruction.dst, instruction.args))
        elif instruction.op == "return" and instruction.dst is None and len(instruction.args) == 1:
            selected.append(VirtualInstruction("RET", srcs=instruction.args))
            continue
        else:
            raise ValueError(f"unsupported or malformed IR instruction: {instruction}")
        if instruction.dst in defined:
            raise ValueError(f"toy selector expects SSA single definition: {instruction.dst}")
        defined.add(instruction.dst)
    return selected


@dataclass(frozen=True)
class LiveInterval:
    name: str
    start: int
    end: int


@dataclass(frozen=True)
class Register:
    name: str


@dataclass(frozen=True)
class Spill:
    slot: int


Location = Register | Spill


def live_intervals(program: Sequence[VirtualInstruction]) -> list[LiveInterval]:
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    for index, instruction in enumerate(program):
        if instruction.dst is not None:
            starts[instruction.dst] = index
            ends[instruction.dst] = index
        for source in instruction.srcs:
            if source not in starts:
                raise ValueError(f"virtual register used before definition: {source}")
            ends[source] = index
    return sorted(
        (LiveInterval(name, start, ends[name]) for name, start in starts.items()),
        key=lambda interval: (interval.start, interval.end, interval.name),
    )


def linear_scan_allocate(
    program: Sequence[VirtualInstruction],
    registers: Sequence[str] = ("R0", "R1"),
) -> dict[str, Location]:
    """简化线性扫描；结果是全程固定 home，spill 使用整数槽位。"""
    free = list(registers)
    if len(set(free)) != len(free):
        raise ValueError("register names must be unique")
    active: list[LiveInterval] = []
    allocation: dict[str, Location] = {}
    next_slot = 0

    def spill(name: str) -> None:
        nonlocal next_slot
        allocation[name] = Spill(next_slot)
        next_slot += 1

    for current in live_intervals(program):
        still_active: list[LiveInterval] = []
        for interval in active:
            if interval.end < current.start:
                location = allocation[interval.name]
                if isinstance(location, Register):
                    free.append(location.name)
            else:
                still_active.append(interval)
        active = sorted(still_active, key=lambda interval: interval.end)
        if free:
            allocation[current.name] = Register(free.pop(0))
            active.append(current)
            active.sort(key=lambda interval: interval.end)
            continue
        if not active:
            spill(current.name)
            continue
        victim = max(active, key=lambda interval: interval.end)
        if victim.end > current.end:
            victim_location = allocation[victim.name]
            assert isinstance(victim_location, Register)
            spill(victim.name)
            allocation[current.name] = victim_location
            active.remove(victim)
            active.append(current)
            active.sort(key=lambda interval: interval.end)
        else:
            spill(current.name)
    return allocation


@dataclass(frozen=True)
class MachineInstruction:
    op: str
    args: tuple[str | int, ...] = ()

    def text(self) -> str:
        return f"{self.op} " + ", ".join(map(str, self.args)) if self.args else self.op


def lower_with_spills(
    program: Sequence[VirtualInstruction], allocation: Mapping[str, Location]
) -> list[MachineInstruction]:
    """使用保留的 S0/S1/S2 scratch 寄存器显式插入 LOAD/STORE。"""
    machine: list[MachineInstruction] = []

    def read(name: str, scratch: str) -> str:
        location = allocation[name]
        if isinstance(location, Register):
            return location.name
        machine.append(MachineInstruction("LOAD", (scratch, location.slot)))
        return scratch

    for instruction in program:
        if instruction.op == "LI":
            location = allocation[instruction.dst or ""]
            target = location.name if isinstance(location, Register) else "S2"
            machine.append(MachineInstruction("LI", (target, instruction.immediate)))
            if isinstance(location, Spill):
                machine.append(MachineInstruction("STORE", (target, location.slot)))
        elif instruction.op in {"ADD", "MUL"}:
            left = read(instruction.srcs[0], "S0")
            right = read(instruction.srcs[1], "S1")
            location = allocation[instruction.dst or ""]
            target = location.name if isinstance(location, Register) else "S2"
            machine.append(MachineInstruction(instruction.op, (target, left, right)))
            if isinstance(location, Spill):
                machine.append(MachineInstruction("STORE", (target, location.slot)))
        elif instruction.op == "RET":
            machine.append(MachineInstruction("RET", (read(instruction.srcs[0], "S0"),)))
        else:
            raise ValueError(f"unsupported virtual instruction: {instruction.op}")
    return machine


def execute(program: Sequence[MachineInstruction]) -> int:
    """执行不含 CALL 的 Toy ISA 算术子集。"""
    registers: dict[str, int] = {}
    slots: dict[int, int] = {}
    for instruction in program:
        if instruction.op == "LI":
            target, value = instruction.args
            registers[str(target)] = int(value)
        elif instruction.op == "LOAD":
            target, slot = instruction.args
            registers[str(target)] = slots[int(slot)]
        elif instruction.op == "STORE":
            source, slot = instruction.args
            slots[int(slot)] = registers[str(source)]
        elif instruction.op in {"ADD", "MUL"}:
            target, left, right = map(str, instruction.args)
            a, b = registers[left], registers[right]
            registers[target] = a + b if instruction.op == "ADD" else a * b
        elif instruction.op == "RET":
            return registers[str(instruction.args[0])]
        else:
            raise ValueError(f"executor does not implement {instruction.op}")
    raise RuntimeError("program terminated without RET")


@dataclass(frozen=True)
class Label:
    name: str


@dataclass(frozen=True)
class Relocation:
    offset: int
    symbol: str


@dataclass(frozen=True)
class ObjectCode:
    words: tuple[int, ...]
    symbols: dict[str, int]
    relocations: tuple[Relocation, ...]


REGISTER_NUMBER = {"R0": 0, "R1": 1, "S0": 2, "S1": 3, "S2": 4}


def _register(name: str | int) -> int:
    if str(name) not in REGISTER_NUMBER:
        raise ValueError(f"unknown Toy ISA register: {name}")
    return REGISTER_NUMBER[str(name)]


def _unsigned_byte(value: str | int, description: str) -> int:
    number = int(value)
    if not 0 <= number <= 255:
        raise ValueError(f"{description} out of range [0, 255]: {number}")
    return number


def _signed_byte(value: str | int, description: str) -> int:
    number = int(value)
    if not -128 <= number <= 127:
        raise ValueError(f"{description} out of range [-128, 127]: {number}")
    return number & 0xFF


def assemble(items: Sequence[Label | MachineInstruction]) -> ObjectCode:
    """编码 16-bit Toy ISA，并为 CALL 留下 signed PC-relative 8-bit relocation。"""
    symbols: dict[str, int] = {}
    offset = 0
    for item in items:
        if isinstance(item, Label):
            if item.name in symbols:
                raise ValueError(f"duplicate symbol: {item.name}")
            symbols[item.name] = offset
        else:
            offset += 1

    words: list[int] = []
    relocations: list[Relocation] = []
    for item in items:
        if isinstance(item, Label):
            continue
        op, args = item.op, item.args
        if op == "NOP" and not args:
            word = 0x0000
        elif op == "LI" and len(args) == 2:
            word = 0x1000 | (_register(args[0]) << 8) | _signed_byte(args[1], "LI immediate")
        elif op in {"ADD", "MUL"} and len(args) == 3:
            opcode = 0x2000 if op == "ADD" else 0x3000
            word = opcode | (_register(args[0]) << 8) | (_register(args[1]) << 4) | _register(args[2])
        elif op in {"LOAD", "STORE"} and len(args) == 2:
            opcode = 0x4000 if op == "LOAD" else 0x5000
            word = opcode | (_register(args[0]) << 8) | _unsigned_byte(args[1], f"{op} slot")
        elif op == "RET" and len(args) == 1:
            word = 0x6000 | (_register(args[0]) << 8)
        elif op == "CALL" and len(args) == 1 and isinstance(args[0], str) and args[0]:
            relocations.append(Relocation(len(words), args[0]))
            word = 0x7000
        else:
            raise ValueError(f"cannot encode Toy ISA instruction: {item}")
        words.append(word)
    return ObjectCode(tuple(words), symbols, tuple(relocations))


def apply_relocations(obj: ObjectCode, external_symbols: Mapping[str, int] | None = None) -> tuple[int, ...]:
    symbols = dict(obj.symbols)
    for name, target in (external_symbols or {}).items():
        if name in symbols and symbols[name] != target:
            raise ValueError(f"conflicting symbol definition: {name}")
        symbols[name] = target
    words = list(obj.words)
    for relocation in obj.relocations:
        if relocation.symbol not in symbols:
            raise ValueError(f"undefined symbol: {relocation.symbol}")
        displacement = symbols[relocation.symbol] - (relocation.offset + 1)
        encoded = _signed_byte(displacement, f"CALL relocation for {relocation.symbol}")
        if words[relocation.offset] & 0xF000 != 0x7000:
            raise ValueError(f"relocation does not point at CALL: {relocation.offset}")
        words[relocation.offset] = 0x7000 | encoded
    return tuple(words)


def demo_ir() -> list[IRInstruction]:
    return [
        IRInstruction("const", "a", immediate=2),
        IRInstruction("const", "b", immediate=3),
        IRInstruction("add", "c", ("a", "b")),
        IRInstruction("mul", "d", ("c", "b")),
        IRInstruction("add", "answer", ("d", "a")),
        IRInstruction("return", args=("answer",)),
    ]


if __name__ == "__main__":
    virtual = select_instructions(demo_ir())
    homes = linear_scan_allocate(virtual, ("R0",))
    machine = lower_with_spills(virtual, homes)
    print("homes:", homes)
    print("machine instructions:")
    print("\n".join(f"  {instruction.text()}" for instruction in machine))
    print("result:", execute(machine))
    obj = assemble([MachineInstruction("CALL", ("helper",)), MachineInstruction("NOP"), Label("helper"), MachineInstruction("RET", ("R0",))])
    print("relocated words:", [f"0x{word:04x}" for word in apply_relocations(obj)])
    print("boundary: invented 16-bit Toy ISA; this is not a real ABI or object format")
