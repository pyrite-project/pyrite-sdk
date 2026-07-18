from dataclasses import dataclass
from typing import TypeAlias


class RFWFormatError(ValueError):
    """Raised when RFW text contains an unterminated or mismatched construct."""

    def __init__(self, message: str, line: int, column: int) -> None:
        self.line = line
        self.column = column
        super().__init__(f"{message} at line {line}, column {column}")


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    line: int
    column: int


@dataclass(frozen=True)
class _Group:
    opener: _Token
    children: tuple["_Node", ...]
    closer: _Token


_Node: TypeAlias = _Token | _Group

_OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = frozenset(_OPEN_TO_CLOSE.values())
_PUNCTUATION = frozenset("()[]{},:;=")


def _tokenize(source: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    line = 1
    column = 1
    length = len(source)

    def advance(text: str) -> None:
        nonlocal line, column
        for character in text:
            if character == "\n":
                line += 1
                column = 1
            else:
                column += 1

    while index < length:
        character = source[index]

        if character.isspace():
            start = index
            while index < length and source[index].isspace():
                index += 1
            advance(source[start:index])
            continue

        token_line = line
        token_column = column

        if character in {'"', "'"}:
            quote = character
            start = index
            index += 1
            escaped = False
            while index < length:
                current = source[index]
                index += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    break
            else:
                raise RFWFormatError("Unterminated string", token_line, token_column)
            value = source[start:index]
            tokens.append(_Token("string", value, token_line, token_column))
            advance(value)
            continue

        if source.startswith("//", index):
            start = index
            newline = source.find("\n", index)
            index = length if newline == -1 else newline
            value = source[start:index].rstrip("\r")
            tokens.append(_Token("line_comment", value, token_line, token_column))
            advance(source[start:index])
            continue

        if source.startswith("/*", index):
            start = index
            end = source.find("*/", index + 2)
            if end == -1:
                raise RFWFormatError("Unterminated block comment", token_line, token_column)
            index = end + 2
            value = source[start:index]
            tokens.append(_Token("block_comment", value, token_line, token_column))
            advance(value)
            continue

        if source.startswith("...", index):
            tokens.append(_Token("ellipsis", "...", token_line, token_column))
            index += 3
            advance("...")
            continue

        if character in _PUNCTUATION:
            tokens.append(_Token("punctuation", character, token_line, token_column))
            index += 1
            advance(character)
            continue

        start = index
        while index < length:
            current = source[index]
            if (
                current.isspace()
                or current in _PUNCTUATION
                or current in {'"', "'"}
                or source.startswith("//", index)
                or source.startswith("/*", index)
                or source.startswith("...", index)
            ):
                break
            index += 1

        if index == start:
            index += 1
        value = source[start:index]
        tokens.append(_Token("word", value, token_line, token_column))
        advance(value)

    return tokens


def _build_groups(tokens: list[_Token]) -> tuple[_Node, ...]:
    def parse(
        index: int,
        opener: _Token | None = None,
    ) -> tuple[tuple[_Node, ...], int, _Token | None]:
        nodes: list[_Node] = []
        expected = _OPEN_TO_CLOSE.get(opener.value) if opener else None

        while index < len(tokens):
            token = tokens[index]
            if token.value in _CLOSERS:
                if expected is None:
                    raise RFWFormatError(
                        f"Unexpected closing delimiter {token.value!r}",
                        token.line,
                        token.column,
                    )
                if token.value != expected:
                    raise RFWFormatError(
                        f"Expected closing delimiter {expected!r}, found {token.value!r}",
                        token.line,
                        token.column,
                    )
                return tuple(nodes), index + 1, token

            if token.value in _OPEN_TO_CLOSE:
                children, index, closer = parse(index + 1, token)
                assert closer is not None
                nodes.append(_Group(token, children, closer))
                continue

            nodes.append(token)
            index += 1

        if opener is not None:
            raise RFWFormatError(
                f"Unclosed delimiter {opener.value!r}",
                opener.line,
                opener.column,
            )
        return tuple(nodes), index, None

    nodes, _, _ = parse(0)
    return nodes


class _Writer:
    def __init__(self, indent_size: int) -> None:
        self.indent_size = indent_size
        self.indent_level = 0
        self.lines: list[str] = []
        self.current = ""

    @property
    def column(self) -> int:
        return self.indent_level * self.indent_size + len(self.current)

    def write(self, value: str) -> None:
        self.current += value

    def space(self) -> None:
        if self.current and not self.current.endswith(" "):
            self.current += " "

    def trim_right(self) -> None:
        self.current = self.current.rstrip()

    def newline(self) -> None:
        if not self.current:
            return
        prefix = " " * (self.indent_level * self.indent_size)
        self.lines.append(prefix + self.current.rstrip())
        self.current = ""

    def blank_line(self) -> None:
        self.newline()
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def finish(self) -> str:
        self.newline()
        while self.lines and self.lines[-1] == "":
            self.lines.pop()
        return "\n".join(self.lines) + ("\n" if self.lines else "")


class _RFWFormatter:
    def __init__(self, indent_size: int, max_line_length: int) -> None:
        self.writer = _Writer(indent_size)
        self.max_line_length = max_line_length

    @staticmethod
    def _group_needs_leading_space(opener: str, previous: _Node | None) -> bool:
        if previous is None:
            return False
        if opener == "{":
            return True
        if opener == "[" and isinstance(previous, _Token) and previous.value == "in":
            return True
        return False

    @staticmethod
    def _is_for_colon(nodes: tuple[_Node, ...], colon_index: int) -> bool:
        values: list[str] = []
        index = colon_index - 1
        while index >= 0:
            node = nodes[index]
            if isinstance(node, _Token) and node.value in {",", ";"}:
                break
            if isinstance(node, _Token):
                values.append(node.value)
            index -= 1
        values.reverse()
        return any(
            values[index : index + 2] == ["...", "for"]
            for index in range(len(values) - 1)
        )

    @staticmethod
    def _has_top_level_comma(group: _Group) -> bool:
        return any(
            isinstance(child, _Token) and child.value == ","
            for child in group.children
        )

    def _flat_group(self, group: _Group) -> str | None:
        if self._has_top_level_comma(group):
            return None
        content = self._flat_nodes(group.children)
        if content is None:
            return None
        return f"{group.opener.value}{content}{group.closer.value}"

    def _flat_nodes(self, nodes: tuple[_Node, ...]) -> str | None:
        result = ""
        previous: _Node | None = None

        for index, node in enumerate(nodes):
            if isinstance(node, _Group):
                group = self._flat_group(node)
                if group is None:
                    return None
                if self._group_needs_leading_space(node.opener.value, previous):
                    result = result.rstrip() + " "
                result += group
                previous = node
                continue

            if node.kind in {"line_comment", "block_comment"} or node.value == ";":
                return None
            if node.value == ",":
                result = result.rstrip() + ", "
            elif node.value == ":":
                if self._is_for_colon(nodes, index):
                    return None
                result = result.rstrip() + ": "
            elif node.value == "=":
                result = result.rstrip() + " = "
            elif node.value == "...":
                if result and not result.endswith((" ", "(", "[", "{")):
                    result += " "
                result += node.value
            else:
                if (
                    result
                    and not result.endswith((" ", "(", "[", "{", "..."))
                ):
                    result += " "
                result += node.value
            previous = node

        return result.rstrip()

    def _write_comment(self, token: _Token) -> None:
        if token.kind == "line_comment":
            self.writer.space()
            self.writer.write(token.value)
            self.writer.newline()
            return

        lines = token.value.splitlines()
        if self.writer.current:
            self.writer.space()
        self.writer.write(lines[0].rstrip())
        for line in lines[1:]:
            self.writer.newline()
            self.writer.write(line.strip())

    def _write_token(
        self,
        token: _Token,
        previous: _Node | None,
        nodes: tuple[_Node, ...],
        index: int,
    ) -> bool:
        if token.kind in {"line_comment", "block_comment"}:
            self._write_comment(token)
            return False
        if token.value == ":":
            self.writer.trim_right()
            self.writer.write(":")
            if self._is_for_colon(nodes, index):
                self.writer.newline()
                return True
            self.writer.space()
            return False
        if token.value == "=":
            self.writer.trim_right()
            self.writer.space()
            self.writer.write("=")
            self.writer.space()
            return False
        if token.value == "...":
            if self.writer.current:
                self.writer.space()
            self.writer.write(token.value)
            return False

        if self.writer.current and not self.writer.current.endswith((" ", "...")):
            self.writer.space()
        self.writer.write(token.value)
        return False

    def _write_group(self, group: _Group, previous: _Node | None) -> None:
        if self._group_needs_leading_space(group.opener.value, previous):
            self.writer.space()

        flat = self._flat_group(group)
        if flat is not None and self.writer.column + len(flat) <= self.max_line_length:
            self.writer.write(flat)
            return

        self.writer.write(group.opener.value)
        if not group.children:
            self.writer.write(group.closer.value)
            return

        self.writer.newline()
        self.writer.indent_level += 1
        self._write_sequence(group.children)
        self.writer.newline()
        self.writer.indent_level -= 1
        self.writer.write(group.closer.value)

    def _write_sequence(self, nodes: tuple[_Node, ...]) -> None:
        previous: _Node | None = None
        loop_body = False
        index = 0

        while index < len(nodes):
            node = nodes[index]
            if isinstance(node, _Group):
                self._write_group(node, previous)
                previous = node
                index += 1
                continue

            if node.value == ",":
                self.writer.trim_right()
                self.writer.write(",")
                if (
                    index + 1 < len(nodes)
                    and isinstance(nodes[index + 1], _Token)
                    and nodes[index + 1].kind == "line_comment"
                ):
                    self._write_comment(nodes[index + 1])
                    index += 1
                else:
                    self.writer.newline()
                if loop_body:
                    self.writer.indent_level -= 1
                    loop_body = False
                previous = node
                index += 1
                continue

            started_loop = self._write_token(node, previous, nodes, index)
            if started_loop:
                self.writer.indent_level += 1
                loop_body = True
            previous = node
            index += 1

        if loop_body:
            self.writer.newline()
            self.writer.indent_level -= 1

    @staticmethod
    def _next_statement_kind(nodes: tuple[_Node, ...], start: int) -> str | None:
        for node in nodes[start:]:
            if isinstance(node, _Token):
                if node.kind in {"line_comment", "block_comment"}:
                    continue
                return node.value
            return None
        return None

    def format(self, nodes: tuple[_Node, ...]) -> str:
        previous: _Node | None = None
        statement_kind: str | None = None
        index = 0

        while index < len(nodes):
            node = nodes[index]
            if isinstance(node, _Group):
                self._write_group(node, previous)
                previous = node
                index += 1
                continue

            if statement_kind is None and node.kind not in {
                "line_comment",
                "block_comment",
            }:
                statement_kind = node.value

            if node.value == ";":
                self.writer.trim_right()
                self.writer.write(";")
                self.writer.newline()
                next_kind = self._next_statement_kind(nodes, index + 1)
                if next_kind is not None and not (
                    statement_kind == "import" and next_kind == "import"
                ):
                    self.writer.blank_line()
                statement_kind = None
            else:
                self._write_token(node, previous, nodes, index)
            previous = node
            index += 1

        return self.writer.finish()


def format_rfw(
    source: str,
    *,
    indent_size: int = 2,
    max_line_length: int = 88,
) -> str:
    """Format RFW source text and return a string ending with one newline.

    The formatter is syntax-aware for strings, comments, delimiters, widget calls,
    lists, maps, switches, events, and ``...for`` list entries. It validates
    balanced delimiters but intentionally leaves semantic validation to the RFW
    runtime.
    """

    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if indent_size < 0:
        raise ValueError("indent_size must be greater than or equal to zero")
    if max_line_length <= 0:
        raise ValueError("max_line_length must be greater than zero")
    if not source.strip():
        return ""

    tokens = _tokenize(source)
    nodes = _build_groups(tokens)
    return _RFWFormatter(indent_size, max_line_length).format(nodes)


__all__ = ["RFWFormatError", "format_rfw"]
