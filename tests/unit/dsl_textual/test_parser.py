"""Tests for the textual DSL parser."""

import pytest

from packages.dsl_core.errors import ParseError
from packages.dsl_core.parser import parse

SIMPLE_SOURCE = """
app UserManagement {
  database: sqlite @path("./data/users.db")
  features: [cors, swagger]
}

entity User {
  email: string @required @email
  name: string @required
}

module Users for User {
  route GET /users -> User[]
}
"""


def test_parser_parses_simple_program() -> None:
    """Parser builds a semantic AST for a simple DSL program."""
    program = parse(SIMPLE_SOURCE)

    assert program.app is not None
    assert program.app.name == "UserManagement"
    assert program.entities[0].name == "User"
    assert program.modules[0].routes[0].path == "/users"
    assert program.modules[0].routes[0].returns_array is True


def test_parser_rejects_entity_inside_module() -> None:
    """Top-level declarations are not valid inside module blocks."""
    source = """
module Users for User {
  entity User {
    email: string
  }
}
"""

    with pytest.raises(ParseError) as error:
        parse(source)

    assert "not allowed inside module" in str(error.value)
