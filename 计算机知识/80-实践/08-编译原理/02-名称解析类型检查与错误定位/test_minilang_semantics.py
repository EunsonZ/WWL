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
