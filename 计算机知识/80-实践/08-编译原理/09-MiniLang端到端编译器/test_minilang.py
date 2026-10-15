import unittest

from minilang import (
    CompileError,
    DEMO_SOURCE,
    If,
    compile_source,
    lex,
    lower_to_ir,
    parse,
    resolve_names,
    type_check,
)


class FrontendAndSemanticsTests(unittest.TestCase):
    def test_decimal_i32_contract_precedes_host_conversion_limit(self) -> None:
        self.assertEqual(lex("return " + "0" * 4301 + "1;")[1].value, 1)
        for digits in ("2147483648", "9" * 4301):
            with self.subTest(digits=digits[:20]):
                with self.assertRaisesRegex(CompileError, r"^lex:1:8: integer literal exceeds i32"):
                    lex("return " + digits + ";")
    def test_tokens_ast_bindings_and_types_are_inspectable(self) -> None:
        tokens = lex(DEMO_SOURCE)
        self.assertEqual(tokens[:5][0].kind, "LET")
        self.assertEqual([token.kind for token in tokens if token.text == "x"], ["IDENT", "IDENT", "IDENT"])
        ast = parse(tokens)
        self.assertEqual(len(ast.statements), 3)
        self.assertIsInstance(ast.statements[2], If)
        bindings = resolve_names(ast)
        self.assertEqual([binding.name for binding in bindings], ["x", "hot", "x"])
        semantics = type_check(ast, bindings)
        self.assertEqual(semantics.symbol_types, (("x", "int"), ("hot", "bool")))

    def test_name_and_type_diagnostics_are_deterministic(self) -> None:
        cases = (
            ("return missing;", "name:1:8: undefined name 'missing'"),
            ("let x: int = true; return x;", "type:1:1: initializer for 'x' has type bool, expected int"),
            ("let x: int = 1; if (x) { return 1; } else { return 0; }", "type:1:21: if condition has type int, expected bool"),
        )
        for source, expected in cases:
            with self.subTest(expected=expected):
                observed: list[str] = []
                for _ in range(2):
                    with self.assertRaises(CompileError) as caught:
                        compile_source(source)
                    observed.append(str(caught.exception))
                self.assertEqual(observed, [expected, expected])


class PipelineTests(unittest.TestCase):
    def test_ir_contains_arithmetic_and_control_flow(self) -> None:
        ast = parse(lex(DEMO_SOURCE))
        type_check(ast, resolve_names(ast))
        text = [instruction.text() for instruction in lower_to_ir(ast)]
        self.assertTrue(any("mul" in line for line in text))
        self.assertTrue(any("branch" in line for line in text))
        self.assertEqual(sum(line.startswith("return") for line in text), 2)

    def test_constant_folding_dce_and_bytecode_preserve_result(self) -> None:
        plain = compile_source(DEMO_SOURCE, optimize_ir=False)
        optimized = compile_source(DEMO_SOURCE, optimize_ir=True)
        self.assertEqual(plain.result, 15)
        self.assertEqual(optimized.result, plain.result)
        self.assertLess(len(optimized.selected_ir), len(plain.selected_ir))
        self.assertLess(len(optimized.bytecode.code), len(plain.bytecode.code))
        self.assertEqual([instruction.text() for instruction in optimized.selected_ir], ["jump then0", "label then0", "return 15"])

    def test_else_branch_executes_before_and_after_optimization(self) -> None:
        source = "let x: int = 2; if (x > 10) { return x + 1; } else { return x * 3; }"
        plain = compile_source(source, optimize_ir=False)
        optimized = compile_source(source)
        self.assertEqual((plain.result, optimized.result), (6, 6))

    def test_complete_compilation_is_reproducible(self) -> None:
        first = compile_source(DEMO_SOURCE)
        second = compile_source(DEMO_SOURCE)
        self.assertEqual(first.tokens, second.tokens)
        self.assertEqual(first.original_ir, second.original_ir)
        self.assertEqual(first.selected_ir, second.selected_ir)
        self.assertEqual(first.bytecode, second.bytecode)


if __name__ == "__main__":
    unittest.main()
