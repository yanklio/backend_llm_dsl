"""Tests for textual DSL blueprint emission."""

from pathlib import Path

import yaml

from packages.dsl_core.compiler import compile_file, compile_textual_dsl
from packages.generator_nestjs.generate import main as generate_project


def test_emitter_matches_simple_blueprint_snapshot() -> None:
    """Simple DSL compiles to the expected existing YAML blueprint shape."""
    source_path = Path("docs/examples/textual_dsl/simple.dsl")
    expected_path = Path("docs/examples/textual_dsl/simple.blueprint.yaml")

    actual = compile_file(source_path)
    expected = yaml.safe_load(expected_path.read_text())

    assert actual == expected


def test_emitter_maps_bidirectional_relations() -> None:
    """Relation annotations are emitted as existing blueprint relations."""
    source = """
entity User {
  posts: Post[] @OneToMany(inverse: author)
}

entity Post {
  author: User @ManyToOne(inverse: posts) @onDelete(CASCADE)
}

module Users for User
"""

    blueprint = compile_textual_dsl(source)
    relation = blueprint["modules"][0]["entity"]["relations"][0]

    assert relation == {
        "type": "OneToMany",
        "model": "Post",
        "field": "posts",
        "required": True,
        "inverseField": "author",
    }


def test_generator_accepts_dsl_input(temp_dir: Path) -> None:
    """Existing generator accepts textual DSL files through the blueprint reader."""
    generate_project("docs/examples/textual_dsl/simple.dsl", str(temp_dir))

    assert (temp_dir / "src" / "user" / "user.module.ts").exists()
    assert (temp_dir / "src" / "user" / "entities" / "user.entity.ts").exists()
