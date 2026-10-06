"""MiniLang 前端的 token、优先级和恢复测试。"""

from __future__ import annotations

import unittest

from minilang_frontend import lex, parse


class FrontendTests(unittest.TestCase):
    def test_maximal_munch_and_spans(self) -> None:
        tokens, errors = lex("let x==10;")
        self.assertEqual(errors, [])
        self.assertEqual([(item.kind, item.text) for item in tokens[:-1]], [("let", "let"), ("IDENT", "x"), ("==", "=="), ("INT", "10"), (";", ";")])
        self.assertEqual(tokens[2].span.start, 5)
        self.assertEqual(tokens[2].span.end, 7)
        self.assertEqual((tokens[2].span.line, tokens[2].span.column), (1, 6))

    def test_pratt_precedence(self) -> None:
        program, errors = parse("print 1 + 2 * 3;")
        self.assertEqual(errors, [])
        expression = program.children[0].children[0]
        self.assertEqual(expression.value, "+")
        self.assertEqual(expression.children[1].value, "*")

    def test_statement_recovery_keeps_next_statement(self) -> None:
        program, errors = parse("let = 1; print 2;")
        self.assertTrue(errors)
        self.assertEqual([statement.kind for statement in program.children], ["let", "print"])
        self.assertEqual(program.children[-1].children[0].value, 2)

    def test_lexical_error_has_source_position(self) -> None:
        _, errors = lex("print @;")
        self.assertEqual(errors[0].message, "unexpected character '@'")
        self.assertEqual((errors[0].span.line, errors[0].span.column), (1, 7))


if __name__ == "__main__":
    unittest.main(verbosity=2)
