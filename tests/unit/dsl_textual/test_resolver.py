"""Tests for textual DSL semantic resolution."""

import pytest

from packages.dsl_core.errors import ResolveError
from packages.dsl_core.parser import parse
from packages.dsl_core.resolver import resolve


def test_resolver_accepts_simple_program() -> None:
    """Resolver accepts a semantically valid program."""
    source = """
entity User {
  email: string @required
}

module Users for User {
  route GET /users -> User[]
}
"""

    resolved = resolve(parse(source))

    assert "User" in resolved.entities


@pytest.mark.parametrize(
    ("source", "code"),
    [
        (
            """
entity User { email: string }
entity User { name: string }
""",
            "RESOLVE_E001",
        ),
        (
            """
entity User { profile: Profile }
""",
            "RESOLVE_E002",
        ),
        (
            """
module Users for Missing {
  route GET /users -> Missing[]
}
""",
            "RESOLVE_E003",
        ),
        (
            """
entity User { email: string }
dto CreateUser for User { missing }
""",
            "RESOLVE_E004",
        ),
        (
            """
entity User { email: string }
module Users for User {
  route GET /users -> Missing[]
}
""",
            "RESOLVE_E005",
        ),
    ],
)
def test_resolver_reports_stable_error_codes(source: str, code: str) -> None:
    """Resolver exposes stable semantic error codes."""
    with pytest.raises(ResolveError) as error:
        resolve(parse(source))

    assert error.value.code == code
