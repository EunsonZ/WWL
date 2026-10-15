"""MiniLang 前端的 token、优先级和恢复测试。"""

from __future__ import annotations

import sys
import unittest

from minilang_frontend import Parser, Span, Token, lex, parse


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


    def test_function_parameter_lists_have_no_spurious_comma(self) -> None:
        for source, names in [
            ("fn f(){ return 1; }", []),
            ("fn f(a){ return a; }", ["a"]),
            ("fn f(a,b,c){ return a; }", ["a", "b", "c"]),
        ]:
            with self.subTest(source=source):
                program, errors = parse(source)
                self.assertEqual(errors, [])
                self.assertEqual([node.value for node in program.children[0].children[:-1]], names)

    def test_missing_parameter_separator_keeps_diagnostic(self) -> None:
        _, errors = parse("fn f(a b){ return a; }")
        self.assertEqual(errors[0].message, "expected ,, found IDENT")
        self.assertEqual((errors[0].span.start, errors[0].span.line, errors[0].span.column), (7, 1, 8))

    def test_unexpected_top_level_close_makes_progress(self) -> None:
        for source, expected in [("}", []), ("} } print 2;", ["print"]), (": } print 2;", ["print"])]:
            with self.subTest(source=source):
                program, errors = parse(source)
                self.assertEqual([node.kind for node in program.children], expected)
                self.assertTrue(errors)
                self.assertEqual(errors[0].span.start, 0)
                self.assertEqual((errors[0].span.line, errors[0].span.column), (1, 1))

    def test_missing_expression_at_eof_has_error_node_and_position(self) -> None:
        for source in ["print", "print 1 +", "print -", "print ("]:
            with self.subTest(source=source):
                program, errors = parse(source)
                eof_errors = [item for item in errors if item.message == "expected expression, found EOF"]
                self.assertEqual(len(eof_errors), 1)
                self.assertEqual((eof_errors[0].span.start, eof_errors[0].span.end), (len(source), len(source)))
                self.assertEqual((eof_errors[0].span.line, eof_errors[0].span.column), (1, len(source) + 1))
                expression = program.children[0].children[0]
                while expression.children:
                    expression = expression.children[-1]
                self.assertEqual(expression.kind, "error")

    def test_nested_block_recovery_preserves_closes_and_later_statements(self) -> None:
        source = "if true { while false { : } print 2; } print 3;"
        program, errors = parse(source)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].message, "expected statement, found :")
        self.assertEqual(errors[0].span.start, source.index(":"))
        self.assertEqual([node.kind for node in program.children], ["if", "print"])
        outer = program.children[0].children[1]
        self.assertEqual([node.kind for node in outer.children], ["while", "print"])
        inner = outer.children[0].children[1]
        self.assertEqual(inner.children, ())
        self.assertEqual(inner.span.end, source.index("}") + 1)
        self.assertEqual(outer.children[1].children[0].value, 2)
        self.assertEqual(program.children[1].children[0].value, 3)

    def test_non_decimal_digit_is_positioned_lexical_error(self) -> None:
        tokens, lex_errors = lex("print ²; print 2;")
        self.assertEqual([token.text for token in tokens if token.kind == "INT"], ["2"])
        self.assertEqual(lex_errors[0].message, "unexpected character '²'")
        self.assertEqual(lex_errors[0].span, Span(6, 7, 1, 7))
        program, errors = parse("print ²; print 2;")
        self.assertEqual(errors[0], lex_errors[0])
        self.assertEqual(program.children[-1].children[0].value, 2)

    def test_ascii_and_unicode_decimal_integer_values(self) -> None:
        for digits, value in [("0", 0), ("12345", 12345), ("١٢", 12), ("１２", 12), ("1٢３", 123)]:
            with self.subTest(digits=digits):
                program, errors = parse("print " + digits + ";")
                self.assertEqual(errors, [])
                node = program.children[0].children[0]
                self.assertEqual((node.kind, node.value), ("int", value))
                self.assertEqual(node.span, Span(6, 6 + len(digits), 1, 7))

    def test_integer_conversion_failure_is_diagnostic(self) -> None:
        # Parser 的公开 token 入口也不能让无法转换的 INT 抛出异常。
        span = Span(0, 1, 1, 1)
        parser = Parser([Token("INT", "²", span), Token("EOF", "", Span(1, 1, 1, 2))])
        node = parser.expression()
        self.assertEqual(node.kind, "error")
        self.assertEqual(parser.errors[0].message, "invalid decimal integer literal")
        self.assertEqual(parser.errors[0].span, span)
        self.assertEqual(parser.current.kind, "EOF")
        # 不修改解释器转换限制；开启限制的环境验证十进制长串也有位置诊断。
        limit = sys.get_int_max_str_digits() if hasattr(sys, "get_int_max_str_digits") else 0
        if limit:
            digits = "1" * (limit + 1)
            program, errors = parse("print " + digits + "; print 2;")
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].message, "invalid decimal integer literal")
            self.assertEqual(errors[0].span, Span(6, 6 + len(digits), 1, 7))
            self.assertEqual(program.children[0].children[0].kind, "error")
            self.assertEqual(program.children[1].children[0].value, 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
