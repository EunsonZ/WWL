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
