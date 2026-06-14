"""Lexer for the textual DSL language."""

from dataclasses import dataclass
from enum import Enum

from .errors import LexError, SourceLocation


class TokenType(str, Enum):
    """Token kinds emitted by the textual DSL lexer."""

    APP = "APP"
    MODULE = "MODULE"
    ENTITY = "ENTITY"
    DTO = "DTO"
    ENUM = "ENUM"
    TYPE = "TYPE"
    FOR = "FOR"
    ROUTE = "ROUTE"
    DATABASE = "DATABASE"
    FEATURES = "FEATURES"
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"
    IDENT = "IDENT"
    STRING = "STRING"
    NUMBER = "NUMBER"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COLON = "COLON"
    ARROW = "ARROW"
    AT = "AT"
    QUESTION = "QUESTION"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"
    SLASH = "SLASH"
    EOF = "EOF"


KEYWORDS = {
    "app": TokenType.APP,
    "module": TokenType.MODULE,
    "entity": TokenType.ENTITY,
    "dto": TokenType.DTO,
    "enum": TokenType.ENUM,
    "type": TokenType.TYPE,
    "for": TokenType.FOR,
    "route": TokenType.ROUTE,
    "database": TokenType.DATABASE,
    "features": TokenType.FEATURES,
    "GET": TokenType.GET,
    "POST": TokenType.POST,
    "PATCH": TokenType.PATCH,
    "DELETE": TokenType.DELETE,
}
SINGLE_CHAR_TOKENS = {
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ":": TokenType.COLON,
    "@": TokenType.AT,
    "?": TokenType.QUESTION,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
    "/": TokenType.SLASH,
}


@dataclass(frozen=True)
class Token:
    """Single token with source location."""

    type: TokenType
    value: str
    line: int
    column: int

    @property
    def location(self) -> SourceLocation:
        """Return token location."""
        return SourceLocation(self.line, self.column)


class Lexer:
    """Converts textual DSL source into tokens."""

    def __init__(self, source: str) -> None:
        """Initialize lexer state."""
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        """Tokenize the complete input source."""
        tokens = []
        while not self._is_at_end():
            char = self._peek()
            if char in " \t\r\n":
                self._consume_whitespace()
            elif char == "#" or (char == "/" and self._peek_next() == "/"):
                self._consume_comment()
            elif char == '"':
                tokens.append(self._string())
            elif char.isalpha() or char == "_":
                tokens.append(self._identifier())
            elif char.isdigit():
                tokens.append(self._number())
            elif char == "-" and self._peek_next() == ">":
                tokens.append(self._make_token(TokenType.ARROW, "->"))
                self._advance()
                self._advance()
            elif char in SINGLE_CHAR_TOKENS:
                token_type = SINGLE_CHAR_TOKENS[char]
                tokens.append(self._make_token(token_type, char))
                self._advance()
            else:
                raise LexError(
                    f"Unknown character '{char}'",
                    SourceLocation(self.line, self.column),
                )

        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return tokens

    def _identifier(self) -> Token:
        start_index = self.index
        start_line = self.line
        start_column = self.column
        while not self._is_at_end() and (self._peek().isalnum() or self._peek() in ["_", "-"]):
            self._advance()
        value = self.source[start_index : self.index]
        return Token(KEYWORDS.get(value, TokenType.IDENT), value, start_line, start_column)

    def _number(self) -> Token:
        start_index = self.index
        start_line = self.line
        start_column = self.column
        while not self._is_at_end() and self._peek().isdigit():
            self._advance()
        if not self._is_at_end() and self._peek() == ".":
            self._advance()
            while not self._is_at_end() and self._peek().isdigit():
                self._advance()
        return Token(
            TokenType.NUMBER,
            self.source[start_index : self.index],
            start_line,
            start_column,
        )

    def _string(self) -> Token:
        start_line = self.line
        start_column = self.column
        self._advance()
        chars = []
        while not self._is_at_end() and self._peek() != '"':
            if self._peek() == "\\":
                self._advance()
                if self._is_at_end():
                    break
            chars.append(self._peek())
            self._advance()
        if self._is_at_end():
            raise LexError("Unterminated string", SourceLocation(start_line, start_column))
        self._advance()
        return Token(TokenType.STRING, "".join(chars), start_line, start_column)

    def _consume_whitespace(self) -> None:
        while not self._is_at_end() and self._peek() in " \t\r\n":
            self._advance()

    def _consume_comment(self) -> None:
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _make_token(self, token_type: TokenType, value: str) -> Token:
        return Token(token_type, value, self.line, self.column)

    def _advance(self) -> str:
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _peek(self) -> str:
        return self.source[self.index]

    def _peek_next(self) -> str:
        if self.index + 1 >= len(self.source):
            return "\0"
        return self.source[self.index + 1]

    def _is_at_end(self) -> bool:
        return self.index >= len(self.source)


def tokenize(source: str) -> list[Token]:
    """Tokenize textual DSL source."""
    return Lexer(source).tokenize()
