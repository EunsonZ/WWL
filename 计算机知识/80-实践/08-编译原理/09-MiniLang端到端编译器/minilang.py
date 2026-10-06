#!/usr/bin/env python3
"""A compact MiniLang compiler: source -> bytecode -> stack VM."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Span:
    offset: int
    line: int
    column: int


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    span: Span
    value: int | None = None


class CompileError(ValueError):
    def __init__(self, stage: str, span: Span, message: str) -> None:
        self.stage = stage
        self.span = span
        self.message = message
        super().__init__(f"{stage}:{span.line}:{span.column}: {message}")


KEYWORDS = {
    "let": "LET",
    "if": "IF",
    "else": "ELSE",
    "return": "RETURN",
    "true": "TRUE",
    "false": "FALSE",
    "int": "INT_TYPE",
    "bool": "BOOL_TYPE",
}
SYMBOLS = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "STAR",
    ">": "GREATER",
    "=": "EQUAL",
    ":": "COLON",
    ";": "SEMICOLON",
    "(": "LPAREN",
    ")": "RPAREN",
    "{": "LBRACE",
    "}": "RBRACE",
}
TOKEN_RE = re.compile(
    r"(?P<SPACE>\s+)|(?P<COMMENT>//[^\n]*)|(?P<NUMBER>[0-9]+)|"
    r"(?P<EQEQ>==)|(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)|(?P<SYMBOL>.)"
)


def lex(source: str) -> tuple[Token, ...]:
    tokens: list[Token] = []
    line = 1
    column = 1
    for match in TOKEN_RE.finditer(source):
        text = match.group(0)
        span = Span(match.start(), line, column)
        kind = match.lastgroup
        if kind == "NUMBER":
            value = int(text)
            if value > 2**31 - 1:
                raise CompileError("lex", span, f"integer literal exceeds i32: {text}")
            tokens.append(Token("NUMBER", text, span, value))
        elif kind == "EQEQ":
            tokens.append(Token("EQEQ", text, span))
        elif kind == "IDENT":
            tokens.append(Token(KEYWORDS.get(text, "IDENT"), text, span))
        elif kind == "SYMBOL":
            if text not in SYMBOLS:
                raise CompileError("lex", span, f"unexpected character {text!r}")
            tokens.append(Token(SYMBOLS[text], text, span))
        if "\n" in text:
            line += text.count("\n")
            column = len(text.rsplit("\n", 1)[1]) + 1
        else:
            column += len(text)
    tokens.append(Token("EOF", "", Span(len(source), line, column)))
    return tuple(tokens)


@dataclass(frozen=True)
class Literal:
    value: int | bool
    span: Span


@dataclass(frozen=True)
class Name:
    name: str
    span: Span


@dataclass(frozen=True)
class Binary:
    op: str
    left: Expr
    right: Expr
    span: Span


Expr = Literal | Name | Binary


@dataclass(frozen=True)
class Let:
    name: str
    annotation: str
    value: Expr
    name_span: Span
    span: Span


@dataclass(frozen=True)
class If:
    condition: Expr
    then_body: tuple[Stmt, ...]
    else_body: tuple[Stmt, ...]
    span: Span


@dataclass(frozen=True)
class Return:
    value: Expr
    span: Span


Stmt = Let | If | Return


@dataclass(frozen=True)
class Program:
    statements: tuple[Stmt, ...]


class Parser:
    def __init__(self, tokens: Sequence[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def accept(self, kind: str) -> Token | None:
        if self.current.kind != kind:
            return None
        token = self.current
        self.index += 1
        return token

    def expect(self, kind: str, description: str) -> Token:
        token = self.accept(kind)
        if token is None:
            raise CompileError("parse", self.current.span, f"expected {description}, got {self.current.kind}")
        return token

    def parse(self) -> Program:
        statements = self.parse_statements("EOF")
        self.expect("EOF", "end of input")
        return Program(statements)

    def parse_statements(self, terminator: str) -> tuple[Stmt, ...]:
        statements: list[Stmt] = []
        while self.current.kind != terminator:
            if self.current.kind == "EOF":
                raise CompileError("parse", self.current.span, f"expected {terminator}")
            statements.append(self.parse_statement())
        return tuple(statements)

    def parse_statement(self) -> Stmt:
        if token := self.accept("LET"):
            name = self.expect("IDENT", "a declaration name")
            self.expect("COLON", "':'")
            type_token = self.current
            if self.accept("INT_TYPE") is None and self.accept("BOOL_TYPE") is None:
                raise CompileError("parse", type_token.span, "expected type int or bool")
            self.expect("EQUAL", "'='")
            value = self.parse_expression()
            self.expect("SEMICOLON", "';'")
            return Let(name.text, type_token.text, value, name.span, token.span)
        if token := self.accept("IF"):
            self.expect("LPAREN", "'('")
            condition = self.parse_expression()
            self.expect("RPAREN", "')'")
            self.expect("LBRACE", "'{'")
            then_body = self.parse_statements("RBRACE")
            self.expect("RBRACE", "'}'")
            self.expect("ELSE", "else")
            self.expect("LBRACE", "'{'")
            else_body = self.parse_statements("RBRACE")
            self.expect("RBRACE", "'}'")
            return If(condition, then_body, else_body, token.span)
        if token := self.accept("RETURN"):
            value = self.parse_expression()
            self.expect("SEMICOLON", "';'")
            return Return(value, token.span)
        raise CompileError("parse", self.current.span, f"expected statement, got {self.current.kind}")

    def parse_expression(self) -> Expr:
        return self.parse_equality()

    def parse_equality(self) -> Expr:
        expression = self.parse_comparison()
        while token := self.accept("EQEQ"):
            expression = Binary("==", expression, self.parse_comparison(), token.span)
        return expression

    def parse_comparison(self) -> Expr:
        expression = self.parse_additive()
        while token := self.accept("GREATER"):
            expression = Binary(">", expression, self.parse_additive(), token.span)
        return expression

    def parse_additive(self) -> Expr:
        expression = self.parse_multiplicative()
        while self.current.kind in {"PLUS", "MINUS"}:
            token = self.current
            self.index += 1
            expression = Binary(token.text, expression, self.parse_multiplicative(), token.span)
        return expression

    def parse_multiplicative(self) -> Expr:
        expression = self.parse_primary()
        while token := self.accept("STAR"):
            expression = Binary("*", expression, self.parse_primary(), token.span)
        return expression

    def parse_primary(self) -> Expr:
        if token := self.accept("NUMBER"):
            assert token.value is not None
            return Literal(token.value, token.span)
        if token := self.accept("TRUE"):
            return Literal(True, token.span)
        if token := self.accept("FALSE"):
            return Literal(False, token.span)
        if token := self.accept("IDENT"):
            return Name(token.text, token.span)
        if self.accept("LPAREN"):
            expression = self.parse_expression()
            self.expect("RPAREN", "')'")
            return expression
        raise CompileError("parse", self.current.span, f"expected expression, got {self.current.kind}")


def parse(tokens: Sequence[Token]) -> Program:
    return Parser(tokens).parse()


@dataclass(frozen=True)
class Binding:
    name: str
    use: Span
    declaration: Span


@dataclass(frozen=True)
class SemanticInfo:
    bindings: tuple[Binding, ...]
    symbol_types: tuple[tuple[str, str], ...]


def _walk_names(expression: Expr, scope: dict[str, Span], bindings: list[Binding]) -> None:
    if isinstance(expression, Name):
        if expression.name not in scope:
            raise CompileError("name", expression.span, f"undefined name '{expression.name}'")
        bindings.append(Binding(expression.name, expression.span, scope[expression.name]))
    elif isinstance(expression, Binary):
        _walk_names(expression.left, scope, bindings)
        _walk_names(expression.right, scope, bindings)


def resolve_names(program: Program) -> tuple[Binding, ...]:
    bindings: list[Binding] = []
    declarations: dict[str, Span] = {}

    def visit(statements: Sequence[Stmt], incoming: dict[str, Span]) -> None:
        scope = dict(incoming)
        for statement in statements:
            if isinstance(statement, Let):
                _walk_names(statement.value, scope, bindings)
                if statement.name in declarations:
                    first = declarations[statement.name]
                    message = (
                        f"duplicate declaration '{statement.name}'; "
                        f"first declared at {first.line}:{first.column}"
                    )
                    raise CompileError("name", statement.name_span, message)
                declarations[statement.name] = statement.name_span
                scope[statement.name] = statement.name_span
            elif isinstance(statement, If):
                _walk_names(statement.condition, scope, bindings)
                visit(statement.then_body, scope)
                visit(statement.else_body, scope)
            else:
                _walk_names(statement.value, scope, bindings)

    visit(program.statements, {})
    return tuple(bindings)


def _expression_type(expression: Expr, scope: dict[str, str]) -> str:
    if isinstance(expression, Literal):
        return "bool" if type(expression.value) is bool else "int"
    if isinstance(expression, Name):
        return scope[expression.name]
    left = _expression_type(expression.left, scope)
    right = _expression_type(expression.right, scope)
    if expression.op in {"+", "-", "*", ">"}:
        if left != "int" or right != "int":
            raise CompileError("type", expression.span, f"operator {expression.op} needs int, got {left} and {right}")
        return "bool" if expression.op == ">" else "int"
    if left != right:
        raise CompileError("type", expression.span, f"operator == needs equal types, got {left} and {right}")
    return "bool"


def _always_returns(statements: Sequence[Stmt]) -> bool:
    for statement in statements:
        if isinstance(statement, Return):
            return True
        if isinstance(statement, If) and _always_returns(statement.then_body) and _always_returns(statement.else_body):
            return True
    return False


def type_check(program: Program, bindings: tuple[Binding, ...]) -> SemanticInfo:
    symbols: list[tuple[str, str]] = []

    def visit(statements: Sequence[Stmt], incoming: dict[str, str]) -> None:
        scope = dict(incoming)
        for statement in statements:
            if isinstance(statement, Let):
                actual = _expression_type(statement.value, scope)
                if actual != statement.annotation:
                    message = f"initializer for '{statement.name}' has type {actual}, expected {statement.annotation}"
                    raise CompileError("type", statement.span, message)
                scope[statement.name] = statement.annotation
                symbols.append((statement.name, statement.annotation))
            elif isinstance(statement, If):
                actual = _expression_type(statement.condition, scope)
                if actual != "bool":
                    raise CompileError("type", statement.condition.span, f"if condition has type {actual}, expected bool")
                visit(statement.then_body, scope)
                visit(statement.else_body, scope)
            else:
                _expression_type(statement.value, scope)

    visit(program.statements, {})
    if not _always_returns(program.statements):
        first = program.statements[0].span if program.statements else Span(0, 1, 1)
        raise CompileError("type", first, "program may finish without return")
    return SemanticInfo(bindings, tuple(symbols))


@dataclass(frozen=True)
class IRInstr:
    op: str
    dest: str | None = None
    args: tuple[str | int | bool, ...] = ()

    def text(self) -> str:
        arguments = ", ".join(repr(item) if type(item) is bool else str(item) for item in self.args)
        prefix = f"{self.dest} = " if self.dest is not None else ""
        return f"{prefix}{self.op}" + (f" {arguments}" if arguments else "")


class IRBuilder:
    def __init__(self) -> None:
        self.instructions: list[IRInstr] = []
        self.temp_index = 0
        self.label_index = 0

    def temp(self) -> str:
        name = f"%t{self.temp_index}"
        self.temp_index += 1
        return name

    def label(self, prefix: str) -> str:
        name = f"{prefix}{self.label_index}"
        self.label_index += 1
        return name

    def expression(self, expression: Expr) -> str:
        if isinstance(expression, Literal):
            target = self.temp()
            self.instructions.append(IRInstr("const", target, (expression.value,)))
            return target
        if isinstance(expression, Name):
            return expression.name
        left = self.expression(expression.left)
        right = self.expression(expression.right)
        target = self.temp()
        operations = {"+": "add", "-": "sub", "*": "mul", ">": "gt", "==": "eq"}
        self.instructions.append(IRInstr(operations[expression.op], target, (left, right)))
        return target

    def statements(self, statements: Sequence[Stmt]) -> None:
        for statement in statements:
            if isinstance(statement, Let):
                self.instructions.append(IRInstr("move", statement.name, (self.expression(statement.value),)))
            elif isinstance(statement, Return):
                self.instructions.append(IRInstr("return", args=(self.expression(statement.value),)))
            else:
                condition = self.expression(statement.condition)
                then_label = self.label("then")
                else_label = self.label("else")
                end_label = self.label("end")
                self.instructions.append(IRInstr("branch", args=(condition, then_label, else_label)))
                self.instructions.append(IRInstr("label", args=(then_label,)))
                self.statements(statement.then_body)
                self.instructions.append(IRInstr("jump", args=(end_label,)))
                self.instructions.append(IRInstr("label", args=(else_label,)))
                self.statements(statement.else_body)
                self.instructions.append(IRInstr("label", args=(end_label,)))


def lower_to_ir(program: Program) -> tuple[IRInstr, ...]:
    builder = IRBuilder()
    builder.statements(program.statements)
    return tuple(builder.instructions)


def _i32(value: int) -> int:
    unsigned = value & 0xFFFFFFFF
    return unsigned if unsigned < 0x80000000 else unsigned - 0x100000000


def _fold(op: str, left: int | bool, right: int | bool) -> int | bool:
    if op == "add":
        return _i32(int(left) + int(right))
    if op == "sub":
        return _i32(int(left) - int(right))
    if op == "mul":
        return _i32(int(left) * int(right))
    if op == "gt":
        return int(left) > int(right)
    return left == right


def constant_fold(code: Sequence[IRInstr]) -> tuple[IRInstr, ...]:
    constants: dict[str, int | bool] = {}
    result: list[IRInstr] = []

    def value(argument: str | int | bool) -> str | int | bool:
        return constants.get(argument, argument) if isinstance(argument, str) else argument

    for instruction in code:
        if instruction.op == "const":
            assert instruction.dest is not None
            constants[instruction.dest] = instruction.args[0]  # type: ignore[assignment]
            result.append(instruction)
        elif instruction.op == "move":
            assert instruction.dest is not None
            source = value(instruction.args[0])
            if not isinstance(source, str):
                constants[instruction.dest] = source
                result.append(IRInstr("const", instruction.dest, (source,)))
            else:
                result.append(IRInstr("move", instruction.dest, (source,)))
        elif instruction.op in {"add", "sub", "mul", "gt", "eq"}:
            assert instruction.dest is not None
            left, right = (value(item) for item in instruction.args)
            if not isinstance(left, str) and not isinstance(right, str):
                folded = _fold(instruction.op, left, right)
                constants[instruction.dest] = folded
                result.append(IRInstr("const", instruction.dest, (folded,)))
            else:
                result.append(IRInstr(instruction.op, instruction.dest, (left, right)))
        elif instruction.op == "branch":
            condition = value(instruction.args[0])
            if type(condition) is bool:
                target = instruction.args[1] if condition else instruction.args[2]
                result.append(IRInstr("jump", args=(target,)))
            else:
                result.append(IRInstr("branch", args=(condition, *instruction.args[1:])))
        elif instruction.op == "return":
            result.append(IRInstr("return", args=(value(instruction.args[0]),)))
        else:
            result.append(instruction)
    return tuple(result)


def _labels(code: Sequence[IRInstr]) -> dict[str, int]:
    return {str(instruction.args[0]): index for index, instruction in enumerate(code) if instruction.op == "label"}


def _successors(code: Sequence[IRInstr], index: int, labels: dict[str, int]) -> tuple[int, ...]:
    instruction = code[index]
    if instruction.op == "return":
        return ()
    if instruction.op == "jump":
        return (labels[str(instruction.args[0])],)
    if instruction.op == "branch":
        return (labels[str(instruction.args[1])], labels[str(instruction.args[2])])
    return (index + 1,) if index + 1 < len(code) else ()


def _uses(instruction: IRInstr) -> set[str]:
    indexes = {
        "move": (0,),
        "add": (0, 1),
        "sub": (0, 1),
        "mul": (0, 1),
        "gt": (0, 1),
        "eq": (0, 1),
        "branch": (0,),
        "return": (0,),
    }.get(instruction.op, ())
    return {str(instruction.args[index]) for index in indexes if isinstance(instruction.args[index], str)}


PURE_DEFINITIONS = {"const", "move", "add", "sub", "mul", "gt", "eq"}


def _reachable(code: Sequence[IRInstr]) -> tuple[IRInstr, ...]:
    if not code:
        return ()
    labels = _labels(code)
    seen: set[int] = set()
    queue = deque([0])
    while queue:
        index = queue.popleft()
        if index in seen:
            continue
        seen.add(index)
        queue.extend(target for target in _successors(code, index, labels) if target not in seen)
    return tuple(instruction for index, instruction in enumerate(code) if index in seen)


def dead_code_eliminate(code: Sequence[IRInstr]) -> tuple[IRInstr, ...]:
    current = _reachable(code)
    while True:
        labels = _labels(current)
        live_in = [set() for _ in current]
        live_out = [set() for _ in current]
        changed = True
        while changed:
            changed = False
            for index in range(len(current) - 1, -1, -1):
                instruction = current[index]
                outgoing: set[str] = set()
                for successor in _successors(current, index, labels):
                    outgoing.update(live_in[successor])
                incoming = _uses(instruction) | (outgoing - ({instruction.dest} if instruction.dest else set()))
                if outgoing != live_out[index] or incoming != live_in[index]:
                    live_out[index] = outgoing
                    live_in[index] = incoming
                    changed = True
        reduced = tuple(
            instruction
            for index, instruction in enumerate(current)
            if not (
                instruction.op in PURE_DEFINITIONS
                and instruction.dest is not None
                and instruction.dest not in live_out[index]
            )
        )
        if reduced == current:
            return current
        current = _reachable(reduced)


def optimize(code: Sequence[IRInstr]) -> tuple[IRInstr, ...]:
    return dead_code_eliminate(constant_fold(code))


@dataclass(frozen=True)
class BytecodeInstr:
    op: str
    arg: int | None = None


@dataclass(frozen=True)
class BytecodeProgram:
    code: tuple[BytecodeInstr, ...]
    constants: tuple[int | bool, ...]
    slots: tuple[str, ...]


def emit_bytecode(ir: Sequence[IRInstr]) -> BytecodeProgram:
    slot_names = tuple(dict.fromkeys(instruction.dest for instruction in ir if instruction.dest is not None))
    slots = {name: index for index, name in enumerate(slot_names)}
    constants: list[int | bool] = []
    constant_indexes: dict[tuple[type, int | bool], int] = {}
    code: list[BytecodeInstr] = []
    labels: dict[str, int] = {}
    patches: list[tuple[int, str]] = []

    def emit_value(argument: str | int | bool) -> None:
        if isinstance(argument, str):
            code.append(BytecodeInstr("LOAD", slots[argument]))
            return
        key = (type(argument), argument)
        if key not in constant_indexes:
            constant_indexes[key] = len(constants)
            constants.append(argument)
        code.append(BytecodeInstr("PUSH", constant_indexes[key]))

    def emit_jump(op: str, label: str) -> None:
        patches.append((len(code), label))
        code.append(BytecodeInstr(op, -1))

    binary_ops = {"add": "ADD", "sub": "SUB", "mul": "MUL", "gt": "GT", "eq": "EQ"}
    for instruction in ir:
        if instruction.op == "label":
            labels[str(instruction.args[0])] = len(code)
        elif instruction.op in {"const", "move"}:
            assert instruction.dest is not None
            emit_value(instruction.args[0])
            code.append(BytecodeInstr("STORE", slots[instruction.dest]))
        elif instruction.op in binary_ops:
            assert instruction.dest is not None
            emit_value(instruction.args[0])
            emit_value(instruction.args[1])
            code.append(BytecodeInstr(binary_ops[instruction.op]))
            code.append(BytecodeInstr("STORE", slots[instruction.dest]))
        elif instruction.op == "branch":
            emit_value(instruction.args[0])
            emit_jump("JUMP_IF_FALSE", str(instruction.args[2]))
            emit_jump("JUMP", str(instruction.args[1]))
        elif instruction.op == "jump":
            emit_jump("JUMP", str(instruction.args[0]))
        elif instruction.op == "return":
            emit_value(instruction.args[0])
            code.append(BytecodeInstr("RETURN"))
        else:
            raise ValueError(f"unknown IR op: {instruction.op}")
    for index, label in patches:
        if label not in labels:
            raise ValueError(f"unknown label: {label}")
        code[index] = BytecodeInstr(code[index].op, labels[label])
    return BytecodeProgram(tuple(code), tuple(constants), slot_names)


def run_vm(program: BytecodeProgram) -> int | bool:
    missing = object()
    local_values: list[object] = [missing] * len(program.slots)
    stack: list[int | bool] = []
    pc = 0
    steps = 0
    while 0 <= pc < len(program.code):
        steps += 1
        if steps > 10_000:
            raise RuntimeError("VM step budget exceeded")
        instruction = program.code[pc]
        pc += 1
        if instruction.op == "PUSH":
            assert instruction.arg is not None
            stack.append(program.constants[instruction.arg])
        elif instruction.op == "LOAD":
            assert instruction.arg is not None
            value = local_values[instruction.arg]
            if value is missing:
                raise RuntimeError(f"read of uninitialized slot {program.slots[instruction.arg]}")
            stack.append(value)  # type: ignore[arg-type]
        elif instruction.op == "STORE":
            assert instruction.arg is not None
            local_values[instruction.arg] = stack.pop()
        elif instruction.op in {"ADD", "SUB", "MUL", "GT", "EQ"}:
            right = stack.pop()
            left = stack.pop()
            stack.append(_fold(instruction.op.lower(), left, right))
        elif instruction.op == "JUMP":
            assert instruction.arg is not None
            pc = instruction.arg
        elif instruction.op == "JUMP_IF_FALSE":
            assert instruction.arg is not None
            condition = stack.pop()
            if type(condition) is not bool:
                raise RuntimeError("non-bool VM branch condition")
            if not condition:
                pc = instruction.arg
        elif instruction.op == "RETURN":
            return stack.pop()
        else:
            raise RuntimeError(f"unknown bytecode op: {instruction.op}")
    raise RuntimeError("VM reached the end without RETURN")


@dataclass(frozen=True)
class Compilation:
    tokens: tuple[Token, ...]
    ast: Program
    semantics: SemanticInfo
    original_ir: tuple[IRInstr, ...]
    selected_ir: tuple[IRInstr, ...]
    bytecode: BytecodeProgram
    result: int | bool


def compile_source(source: str, *, optimize_ir: bool = True) -> Compilation:
    tokens = lex(source)
    ast = parse(tokens)
    bindings = resolve_names(ast)
    semantics = type_check(ast, bindings)
    original = lower_to_ir(ast)
    selected = optimize(original) if optimize_ir else original
    bytecode = emit_bytecode(selected)
    return Compilation(tokens, ast, semantics, original, selected, bytecode, run_vm(bytecode))


DEMO_SOURCE = """\
let x: int = 2 + 3 * 4;
let hot: bool = x > 10;
if (hot) {
  return x + 1;
} else {
  return 0;
}
"""


def _lines(instructions: Iterable[IRInstr]) -> str:
    return "\n".join(f"  {instruction.text()}" for instruction in instructions)


def main() -> None:
    compilation = compile_source(DEMO_SOURCE)
    print("TOKENS", [token.kind for token in compilation.tokens])
    print("BINDINGS", compilation.semantics.bindings)
    print("ORIGINAL IR\n" + _lines(compilation.original_ir))
    print("OPTIMIZED IR\n" + _lines(compilation.selected_ir))
    print("BYTECODE", compilation.bytecode)
    print("RESULT", compilation.result)


if __name__ == "__main__":
    main()
