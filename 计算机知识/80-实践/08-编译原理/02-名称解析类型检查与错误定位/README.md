---
type: practice
stage: 3
status: ready
difficulty: 中级
estimated_minutes: 45
domain: computer-science
tags:
  - computer-science/compiler
  - computer-science/name-resolution
  - computer-science/type-checking
---

# MiniLang 名称解析、类型检查与错误定位

本实验延续 MiniLang 的 i32 / bool 约定，展示“同名不是同一变量”：解析器按作用域栈声明 Symbol(identity, name, type)，表达式保存解析到的 symbol 身份。类型检查器在已解析 AST 上检查 let、条件、函数返回、调用 arity 与 i32/bool 运算冲突，并将错误绑定到提供的行列 span。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/08-编译原理/02-名称解析类型检查与错误定位"
python3 -m unittest -v
~~~

预期 Ran 3 tests ... OK。观察内层 x: bool 与外层 x: i32 有不同 identity；重复声明和未声明名称分别报告声明点与使用点；id 的实参数错误与 bool + i32 错误的定位保持确定顺序。

安全边界：仅 Python 标准库和构造式 AST，不读写用户文件、不联网、不安装、不运行待分析程序。测试可能产生同目录 __pycache__/；确认后可删除，源码可由 Git diff 或编辑器撤销恢复。范围诚实说明：这里没有把实验 01 的 AST 接线进来，也没有类型推断、泛型、闭包捕获、控制流 definite-assignment、赋值 target 的完整 AST 或函数参数类型的调用逐参数检查；它是专注 identity/诊断的可执行切片，非完整语义分析器。

练习：给函数 symbol 保存参数类型，并在调用点逐参数比较；再为 while 条件非 bool 加测试。成功标准是解析前的所有名称都能显式解析或得到一个位置诊断，新增规则不会把同名 shadowing 合并为同一 symbol。

相关稳定课：[[计算机知识/10-编程语言/01-Python/03-控制流函数与作用域|计算机知识/10-编程语言/01-Python/03-控制流函数与作用域]]、[[计算机知识/10-编程语言/02-C++/02-语法类型与函数|计算机知识/10-编程语言/02-C++/02-语法类型与函数]]。

<!-- code-sync: ./minilang_semantics.py -->
~~~python
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
~~~

<!-- code-sync: ./test_minilang_semantics.py -->
~~~python
"""MiniLang 构造式语义实验的身份、名称、调用和类型诊断测试。"""

from __future__ import annotations

import unittest

from minilang_semantics import BOOL, I32, Expr, Resolver, Span, Stmt, TypeChecker, boolean, integer, name


class SemanticTests(unittest.TestCase):
    def test_shadowing_has_distinct_symbol_identity(self) -> None:
        outer_use = name("x", 4, 7)
        inner_use = name("x", 3, 9)
        program = [Stmt("let", Span(1, 1), "x", I32, integer(1)), Stmt("if", Span(2, 1), expr=boolean(True), body=[Stmt("let", Span(3, 3), "x", BOOL, boolean(False)), Stmt("print", Span(3, 8), expr=inner_use)]), Stmt("print", Span(4, 1), expr=outer_use)]
        resolver = Resolver()
        self.assertEqual(resolver.resolve(program), [])
        self.assertNotEqual(inner_use.symbol.identity, outer_use.symbol.identity)
        self.assertEqual((inner_use.symbol.typ, outer_use.symbol.typ), (BOOL, I32))

    def test_duplicate_and_undeclared_names_report_their_spans(self) -> None:
        missing = name("gone", 3, 7)
        program = [Stmt("let", Span(1, 1), "x", I32, integer(1)), Stmt("let", Span(2, 1), "x", I32, integer(2)), Stmt("print", Span(3, 1), expr=missing)]
        errors = Resolver().resolve(program)
        self.assertEqual([(error.message, error.span.line, error.span.column) for error in errors], [("duplicate declaration of x", 2, 1), ("undeclared name gone", 3, 7)])

    def test_arity_and_i32_bool_conflicts_are_diagnostic(self) -> None:
        callee = name("id", 5, 1)
        program = [Stmt("fn", Span(1, 1), "id", body=[Stmt("return", Span(2, 3), expr=name("a", 2, 10))], params=[("a", I32, Span(1, 7))], result=I32), Stmt("let", Span(4, 1), "flag", BOOL, boolean(True)), Stmt("print", Span(5, 1), expr=Expr("call", Span(5, 1), children=[callee, boolean(False), integer(7)])), Stmt("let", Span(6, 1), "bad", I32, Expr("+", Span(6, 15), children=[name("flag", 6, 15), integer(1, 6, 22)]))]
        resolver = Resolver()
        self.assertEqual(resolver.resolve(program), [])
        errors = TypeChecker().check(program)
        self.assertEqual([error.message for error in errors], ["arity mismatch: id expects 1, got 2", "+ requires i32 operands"])
        self.assertEqual([(error.span.line, error.span.column) for error in errors], [(5, 1), (6, 15)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
~~~

返回 [[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践 MOC]]。



<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
