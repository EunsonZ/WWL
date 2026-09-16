"""构造式 MiniLang AST 的符号身份、名称解析、类型检查和 span 诊断。"""

from __future__ import annotations

from dataclasses import dataclass, field


I32 = "i32"
BOOL = "bool"
UNIT = "unit"


@dataclass(frozen=True)
class Span:
    line: int
    column: int


@dataclass
class Diagnostic:
    message: str
    span: Span


@dataclass
class Expr:
    kind: str
    span: Span
    value: object = None
    children: list["Expr"] = field(default_factory=list)
    symbol: "Symbol | None" = None


@dataclass
class Stmt:
    kind: str
    span: Span
    name: str | None = None
    annotation: str | None = None
    expr: Expr | None = None
    body: list["Stmt"] = field(default_factory=list)
    otherwise: list["Stmt"] = field(default_factory=list)
    params: list[tuple[str, str, Span]] = field(default_factory=list)
    result: str | None = None


@dataclass(frozen=True)
class Symbol:
    identity: int
    name: str
    typ: str
    arity: int | None = None


class Resolver:
    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]
        self.errors: list[Diagnostic] = []
        self.next_identity = 0

    def declare(self, name: str, typ: str, span: Span, arity: int | None = None) -> Symbol | None:
        if name in self.scopes[-1]:
            self.errors.append(Diagnostic(f"duplicate declaration of {name}", span))
            return None
        symbol = Symbol(self.next_identity, name, typ, arity)
        self.next_identity += 1
        self.scopes[-1][name] = symbol
        return symbol

    def lookup(self, name: str, span: Span) -> Symbol | None:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        self.errors.append(Diagnostic(f"undeclared name {name}", span))
        return None

    def resolve_expr(self, expression: Expr) -> None:
        if expression.kind == "name":
            expression.symbol = self.lookup(str(expression.value), expression.span)
        for child in expression.children:
            self.resolve_expr(child)

    def resolve_block(self, statements: list[Stmt]) -> None:
        self.scopes.append({})
        for statement in statements:
            self.resolve_stmt(statement)
        self.scopes.pop()

    def resolve_stmt(self, statement: Stmt) -> None:
        if statement.kind == "let":
            if statement.expr:
                self.resolve_expr(statement.expr)
            self.declare(statement.name or "<missing>", statement.annotation or I32, statement.span)
        elif statement.kind == "fn":
            self.declare(statement.name or "<missing>", statement.result or I32, statement.span, len(statement.params))
            self.scopes.append({})
            for name, typ, span in statement.params:
                self.declare(name, typ, span)
            for child in statement.body:
                self.resolve_stmt(child)
            self.scopes.pop()
        else:
            if statement.expr:
                self.resolve_expr(statement.expr)
            if statement.kind == "assign" and statement.name:
                self.lookup(statement.name, statement.span)
            if statement.kind in {"if", "while"}:
                self.resolve_block(statement.body)
                self.resolve_block(statement.otherwise)

    def resolve(self, program: list[Stmt]) -> list[Diagnostic]:
        for statement in program:
            self.resolve_stmt(statement)
        return self.errors


class TypeChecker:
    def __init__(self) -> None:
        self.errors: list[Diagnostic] = []
        self.function_returns: list[str] = []

    def error(self, message: str, span: Span) -> None:
        self.errors.append(Diagnostic(message, span))

    def expr_type(self, expression: Expr) -> str:
        if expression.kind == "int":
            return I32
        if expression.kind == "bool":
            return BOOL
        if expression.kind == "name":
            return expression.symbol.typ if expression.symbol else "error"
        if expression.kind == "call":
            callee = expression.children[0]
            if callee.symbol is None or callee.symbol.arity is None:
                self.error("call target is not a function", callee.span)
                return "error"
            arguments = expression.children[1:]
            if len(arguments) != callee.symbol.arity:
                self.error(f"arity mismatch: {callee.symbol.name} expects {callee.symbol.arity}, got {len(arguments)}", expression.span)
            for argument in arguments:
                self.expr_type(argument)
            return callee.symbol.typ
        if expression.kind in {"+", "-", "*", "/"}:
            left, right = (self.expr_type(child) for child in expression.children)
            if left != I32 or right != I32:
                self.error(f"{expression.kind} requires i32 operands", expression.span)
            return I32
        if expression.kind in {"==", "!="}:
            left, right = (self.expr_type(child) for child in expression.children)
            if left != right:
                self.error("comparison operands must have the same type", expression.span)
            return BOOL
        if expression.kind in {"&&", "||"}:
            left, right = (self.expr_type(child) for child in expression.children)
            if left != BOOL or right != BOOL:
                self.error(f"{expression.kind} requires bool operands", expression.span)
            return BOOL
        self.error(f"unknown expression kind {expression.kind}", expression.span)
        return "error"

    def check_block(self, statements: list[Stmt]) -> None:
        for statement in statements:
            self.check_stmt(statement)

    def check_stmt(self, statement: Stmt) -> None:
        if statement.kind == "let" and statement.expr:
            actual = self.expr_type(statement.expr)
            if actual != statement.annotation:
                self.error(f"initializer is {actual}, declaration requires {statement.annotation}", statement.span)
        elif statement.kind == "assign" and statement.expr:
            target = statement.expr.symbol if statement.expr.kind == "name" else None
            actual = self.expr_type(statement.expr)
            if target and target.typ != actual:
                self.error(f"assignment requires {target.typ}, got {actual}", statement.span)
        elif statement.kind in {"print", "return"} and statement.expr:
            actual = self.expr_type(statement.expr)
            if statement.kind == "return" and self.function_returns and actual != self.function_returns[-1]:
                self.error(f"return requires {self.function_returns[-1]}, got {actual}", statement.span)
        elif statement.kind == "fn":
            self.function_returns.append(statement.result or I32)
            self.check_block(statement.body)
            self.function_returns.pop()
        elif statement.kind in {"if", "while"}:
            if statement.expr and self.expr_type(statement.expr) != BOOL:
                self.error(f"{statement.kind} condition requires bool", statement.expr.span)
            self.check_block(statement.body)
            self.check_block(statement.otherwise)

    def check(self, program: list[Stmt]) -> list[Diagnostic]:
        self.check_block(program)
        return self.errors


def name(value: str, line: int, column: int) -> Expr:
    return Expr("name", Span(line, column), value)


def integer(value: int, line: int = 1, column: int = 1) -> Expr:
    return Expr("int", Span(line, column), value)


def boolean(value: bool, line: int = 1, column: int = 1) -> Expr:
    return Expr("bool", Span(line, column), value)
