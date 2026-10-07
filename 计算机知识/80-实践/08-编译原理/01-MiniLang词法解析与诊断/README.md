---
type: practice
stage: 3
status: ready
difficulty: 中级
estimated_minutes: 50
domain: computer-science
tags:
  - computer-science/compiler
  - computer-science/lexer
  - computer-science/parser
---

# MiniLang 词法、解析与诊断

本实验实现统一 toy MiniLang 的前端切片：i32 整数字面量、bool、let、赋值、if/else、while、fn、return、print，以及算术、比较和布尔表达式。词法器给每个 token 标注 offset 与行/列；多字符运算符先匹配，故 == 不会误切成两个 =。Pratt parser 用绑定强度处理表达式优先级，并以分号或右花括号为同步点作语句级恢复。

## 运行、观察与成功标准

~~~sh
cd "计算机知识/80-实践/08-编译原理/01-MiniLang词法解析与诊断"
python3 -m unittest -v
~~~

预期 Ran 12 tests ... OK。观察 let x==10; 中 == 的 span 为 offset [5, 7)、行 1 列 6；观察 print 1 + 2 * 3; 的 AST 根为 +，其右孩子为 *。把 let = 1; 放在 print 2; 前，诊断出现后仍能保留后一个语句。

恢复的职责按位置区分：块内遇到 `}` 时把它留给 `block()` 配对；顶层的孤立 `}` 已有“expected statement”诊断，必须消费后继续，否则会反复在同一 token 上停住。`if true { while false { : } print 2; } print 3;` 在冒号处诊断一次，仍保留两个后续 print 和两个块的闭括号。表达式遇到 EOF 时返回原 EOF span 的 error 节点，不消费 EOF；例如 `print` 的缺表达式诊断在 offset [5, 5)、行 1 列 6，缺分号诊断也保留，解析返回 AST 与诊断而不越界。参数之间才要求逗号：`fn f(){ return 1; }`、`fn f(a){ return a; }` 和多参数版本都不应因最后一个参数产生假诊断；`fn f(a b){ return a; }` 仍诊断缺逗号。这是本切片的恢复边界，未声称能为所有错误程序保留全部后续声明。

本切片的整数词素接受 Unicode 十进制数字（Python `isdecimal()`，Unicode Nd），保留 `12345`、阿拉伯-印度数字 `١٢`、全角数字 `１２` 以及混合十进制写法 `1٢３` 的数值与原 span。上标 `²` 虽满足 `isdigit()`，却不是十进制数字；在 `print ²;` 中应得到 offset [6, 7)、行 1 列 7 的未知字符诊断，不交给 `int()` 触发异常。此规则没有把已有 Unicode Nd 收窄成 ASCII。若 INT token 无法转换（例如手工构造错误 token，或十进制串超过当前 Python 已启用的转换长度限制），parser 在整个 token span 给出 `invalid decimal integer literal` 并返回 error 节点；不调整解释器限制。Python 整数值暂不做 i32 范围检查，目标 i32 的范围与类型合法性仍需后续语义阶段核验；词法和解析通过不等于这个阶段已通过。

安全边界：只使用 Python 标准库、固定输入和内存数据；不会访问网络、安装依赖、执行 MiniLang、读取或写入用户文件。运行 unittest 可能产生同目录 __pycache__/；可在确认路径后删除；恢复源码使用编辑器撤销或 Git diff。本切片没有字符串、注释嵌套、调用表达式、类型注解、完整声明同步或解释器，因此“解析成功”不代表程序可执行。

练习：为 // 注释加入块注释并为未闭合注释诊断 span；再为函数调用加入后缀 Pratt parselet，并补一个只覆盖新增语义的测试。成功标准是新增测试确定性通过、诊断定位到原始字符位置，且不改变已有 maximal-munch 和恢复测试。

相关稳定课：[[计算机知识/10-编程语言/02-C++/01-编译链接与CMake|计算机知识/10-编程语言/02-C++/01-编译链接与CMake]]、[[计算机知识/10-编程语言/02-C++/02-语法类型与函数|计算机知识/10-编程语言/02-C++/02-语法类型与函数]]、[[计算机知识/10-编程语言/01-Python/03-控制流函数与作用域|计算机知识/10-编程语言/01-Python/03-控制流函数与作用域]]。

<!-- code-sync: ./minilang_frontend.py -->
~~~python
"""MiniLang 的 span 词法器、Pratt 表达式分析和语句级错误恢复。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    line: int
    column: int


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    span: Span


@dataclass(frozen=True)
class Diagnostic:
    message: str
    span: Span


@dataclass(frozen=True)
class Node:
    kind: str
    span: Span
    value: object = None
    children: tuple["Node", ...] = ()


KEYWORDS = {"let", "if", "else", "while", "fn", "return", "print", "true", "false"}
MULTI = ("==", "!=", "<=", ">=", "&&", "||")
SINGLE = set("+-*/<>=!(){};,:")


def lex(source: str) -> tuple[list[Token], list[Diagnostic]]:
    """扫描 UTF-8 Python 字符串；每个 token/诊断保留 0-based offset 和 1-based 行列。"""
    tokens: list[Token] = []
    errors: list[Diagnostic] = []
    index = 0
    line = 1
    column = 1

    def span(start: int, start_line: int, start_column: int) -> Span:
        return Span(start, index, start_line, start_column)

    def advance() -> str:
        nonlocal index, line, column
        char = source[index]
        index += 1
        if char == "\n":
            line += 1
            column = 1
        else:
            column += 1
        return char

    while index < len(source):
        char = source[index]
        if char.isspace():
            advance()
            continue
        start, start_line, start_column = index, line, column
        if source.startswith("//", index):
            while index < len(source) and source[index] != "\n":
                advance()
            continue
        if char.isalpha() or char == "_":
            while index < len(source) and (source[index].isalnum() or source[index] == "_"):
                advance()
            text = source[start:index]
            tokens.append(Token(text if text in KEYWORDS else "IDENT", text, span(start, start_line, start_column)))
            continue
        if char.isdecimal():
            while index < len(source) and source[index].isdecimal():
                advance()
            tokens.append(Token("INT", source[start:index], span(start, start_line, start_column)))
            continue
        operator = next((item for item in MULTI if source.startswith(item, index)), None)
        if operator is not None:
            for _ in operator:
                advance()
            tokens.append(Token(operator, operator, span(start, start_line, start_column)))
            continue
        if char in SINGLE:
            advance()
            tokens.append(Token(char, char, span(start, start_line, start_column)))
            continue
        advance()
        errors.append(Diagnostic(f"unexpected character {char!r}", span(start, start_line, start_column)))
    eof = Span(index, index, line, column)
    tokens.append(Token("EOF", "", eof))
    return tokens, errors


class Parser:
    PRECEDENCE = {"||": 1, "&&": 2, "==": 3, "!=": 3, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6}

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens, self.index, self.errors = tokens, 0, []

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def take(self, kind: str) -> Token | None:
        if self.current.kind == kind:
            token = self.current
            self.index += 1
            return token
        self.errors.append(Diagnostic(f"expected {kind}, found {self.current.kind}", self.current.span))
        return None

    def parse_program(self) -> Node:
        statements: list[Node] = []
        start = self.current.span
        while self.current.kind != "EOF":
            before = self.index
            statement = self.statement()
            if statement is not None:
                statements.append(statement)
            if self.index == before:
                self.recover()
                # 顶层没有可配对的右花括号；块内恢复仍把它留给 block()。
                if self.index == before and self.current.kind != "EOF":
                    self.index += 1
        return Node("program", Span(start.start, self.current.span.end, start.line, start.column), children=tuple(statements))

    def statement(self) -> Node | None:
        token = self.current
        if token.kind == "let":
            self.index += 1
            name = self.take("IDENT")
            self.take("=")
            value = self.expression()
            end = self.take(";") or value.span
            return Node("let", Span(token.span.start, end.span.end if isinstance(end, Token) else end.end, token.span.line, token.span.column), name.text if name else "<error>", (value,))
        if token.kind == "IDENT" and self.tokens[self.index + 1].kind == "=":
            self.index += 2
            value = self.expression()
            end = self.take(";") or value.span
            return Node("assign", Span(token.span.start, end.span.end if isinstance(end, Token) else end.end, token.span.line, token.span.column), token.text, (value,))
        if token.kind == "print":
            self.index += 1
            value = self.expression()
            end = self.take(";") or value.span
            return Node("print", Span(token.span.start, end.span.end if isinstance(end, Token) else end.end, token.span.line, token.span.column), children=(value,))
        if token.kind == "return":
            self.index += 1
            value = self.expression()
            end = self.take(";") or value.span
            return Node("return", Span(token.span.start, end.span.end if isinstance(end, Token) else end.end, token.span.line, token.span.column), children=(value,))
        if token.kind == "if":
            self.index += 1
            condition = self.expression()
            then = self.block()
            if self.current.kind == "else":
                self.index += 1
                otherwise = self.block()
            else:
                otherwise = None
            children = (condition, then) + ((otherwise,) if otherwise else ())
            return Node("if", Span(token.span.start, children[-1].span.end, token.span.line, token.span.column), children=children)
        if token.kind == "while":
            self.index += 1
            condition = self.expression()
            body = self.block()
            return Node("while", Span(token.span.start, body.span.end, token.span.line, token.span.column), children=(condition, body))
        if token.kind == "fn":
            self.index += 1
            name = self.take("IDENT")
            self.take("(")
            params: list[Node] = []
            while self.current.kind not in {")", "EOF"}:
                param = self.take("IDENT")
                if param:
                    params.append(Node("param", param.span, param.text))
                if self.current.kind != ")" and not self.take(","):
                    break
            self.take(")")
            body = self.block()
            return Node("fn", Span(token.span.start, body.span.end, token.span.line, token.span.column), name.text if name else "<error>", tuple(params + [body]))
        self.errors.append(Diagnostic(f"expected statement, found {token.kind}", token.span))
        return None

    def block(self) -> Node:
        open_brace = self.take("{")
        start = open_brace.span if open_brace else self.current.span
        statements: list[Node] = []
        while self.current.kind not in {"}", "EOF"}:
            before = self.index
            statement = self.statement()
            if statement:
                statements.append(statement)
            if self.index == before:
                self.recover()
        close_brace = self.take("}")
        end = close_brace.span.end if close_brace else self.current.span.end
        return Node("block", Span(start.start, end, start.line, start.column), children=tuple(statements))

    def expression(self, minimum: int = 0) -> Node:
        token = self.current
        if token.kind == "EOF":
            self.errors.append(Diagnostic("expected expression, found EOF", token.span))
            return Node("error", token.span)
        self.index += 1
        if token.kind == "INT":
            try:
                value = int(token.text)
            except ValueError:
                self.errors.append(Diagnostic("invalid decimal integer literal", token.span))
                left = Node("error", token.span)
            else:
                left = Node("int", token.span, value)
        elif token.kind in {"true", "false"}:
            left = Node("bool", token.span, token.kind == "true")
        elif token.kind == "IDENT":
            left = Node("name", token.span, token.text)
        elif token.kind in {"-", "!"}:
            operand = self.expression(7)
            left = Node("prefix", Span(token.span.start, operand.span.end, token.span.line, token.span.column), token.kind, (operand,))
        elif token.kind == "(":
            left = self.expression()
            self.take(")")
        else:
            self.errors.append(Diagnostic(f"expected expression, found {token.kind}", token.span))
            left = Node("error", token.span)
        while self.current.kind in self.PRECEDENCE and self.PRECEDENCE[self.current.kind] >= minimum:
            operator = self.current
            precedence = self.PRECEDENCE[operator.kind]
            self.index += 1
            right = self.expression(precedence + 1)
            left = Node("binary", Span(left.span.start, right.span.end, left.span.line, left.span.column), operator.kind, (left, right))
        return left

    def recover(self) -> None:
        while self.current.kind not in {";", "}", "EOF"}:
            self.index += 1
        if self.current.kind == ";":
            self.index += 1


def parse(source: str) -> tuple[Node, list[Diagnostic]]:
    tokens, lex_errors = lex(source)
    parser = Parser(tokens)
    return parser.parse_program(), lex_errors + parser.errors
~~~

<!-- code-sync: ./test_minilang_frontend.py -->
~~~python
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
~~~

返回 [[计算机知识/80-实践/08-编译原理/00-编译原理实践-MOC|编译原理实践 MOC]]。



<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/12-编译原理-课程地图|编译原理 · 课程地图]]。进一步的机制推演与反例：[[计算机知识/70-编译原理/19-从表达式到机器码的贯通推演|编译原理深化：从一条表达式贯通全部阶段]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
