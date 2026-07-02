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

module Users for User
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
module Users for Missing
""",
            "RESOLVE_E003",
        ),
    ],
)
def test_resolver_reports_stable_error_codes(source: str, code: str) -> None:
    """Resolver exposes stable semantic error codes."""
    with pytest.raises(ResolveError) as error:
        resolve(parse(source))

    assert error.value.code == code


def test_resolver_rejects_entity_reference_without_relation() -> None:
    """Entity references must be explicit relations."""
    with pytest.raises(ResolveError) as error:
        resolve(
            parse("""
entity User { email: string }
entity Order { user: User }
""")
        )

    assert error.value.code == "RESOLVE_E006"


def test_resolver_rejects_invalid_relation_cardinality() -> None:
    """Array relation annotations must use array field types."""
    with pytest.raises(ResolveError) as error:
        resolve(
            parse("""
entity User { posts: Post @OneToMany(inverse: author) }
entity Post { author: User @ManyToOne(inverse: posts) }
""")
        )

    assert error.value.code == "RESOLVE_E007"


def test_resolver_rejects_unknown_inverse_field() -> None:
    """Inverse relation fields must exist on the target entity."""
    with pytest.raises(ResolveError) as error:
        resolve(
            parse("""
entity User { posts: Post[] @OneToMany(inverse: owner) }
entity Post { author: User @ManyToOne(inverse: posts) }
""")
        )

    assert error.value.code == "RESOLVE_E008"


def test_resolver_rejects_incompatible_inverse_relation() -> None:
    """Inverse relation annotations must have compatible cardinality."""
    with pytest.raises(ResolveError) as error:
        resolve(
            parse("""
entity User { posts: Post[] @OneToMany(inverse: authors) }
entity Post { authors: User[] @ManyToMany(inverse: posts) }
""")
        )

    assert error.value.code == "RESOLVE_E009"
