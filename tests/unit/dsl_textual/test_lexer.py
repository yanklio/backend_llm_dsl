"""Tests for the textual DSL lexer."""

import pytest

from src.dsl.textual.errors import LexError
from src.dsl.textual.lexer import TokenType, tokenize


def test_lexer_tokenizes_module_header() -> None:
    """Lexer emits expected tokens and source positions for a module header."""
    tokens = tokenize("module Users for User {")

    assert [token.type for token in tokens[:5]] == [
        TokenType.MODULE,
        TokenType.IDENT,
        TokenType.FOR,
        TokenType.IDENT,
        TokenType.LBRACE,
    ]
    assert tokens[0].line == 1
    assert tokens[0].column == 1
    assert tokens[1].value == "Users"


def test_lexer_rejects_unknown_character() -> None:
    """Lexer raises a lexical error for unsupported characters."""
    with pytest.raises(LexError) as error:
        tokenize("entity User { email: string $ }")

    assert "Unknown character '$'" in str(error.value)
