"""Tests for prompt-alignment judging helpers."""

import pytest

from src.llm.prompt_alignment import (
    collect_generated_typescript,
    parse_alignment_response,
)


def test_parse_alignment_response_normalizes_valid_json() -> None:
    """It should parse the simple prompt-alignment schema."""
    result = parse_alignment_response(
        """
        {
          "alignment_score": 4,
          "missing_requirements": ["PUT /users/:id"],
          "extra_features": [],
          "rationale": "Most requested user CRUD pieces are present."
        }
        """
    )

    assert result == {
        "alignment_score": 4,
        "missing_requirements": ["PUT /users/:id"],
        "extra_features": [],
        "rationale": "Most requested user CRUD pieces are present.",
    }


def test_parse_alignment_response_rejects_out_of_range_score() -> None:
    """It should reject scores outside the thesis rubric range."""
    with pytest.raises(ValueError, match="alignment_score"):
        parse_alignment_response(
            '{"alignment_score": 6, "missing_requirements": [], "extra_features": [], "rationale": ""}'
        )


def test_collect_generated_typescript_reads_src_files(temp_dir) -> None:
    """It should collect generated TypeScript files relative to the project root."""
    source_dir = temp_dir / "src" / "user"
    source_dir.mkdir(parents=True)
    (source_dir / "user.controller.ts").write_text("export class UserController {}")
    (temp_dir / "src" / "README.md").write_text("ignored")

    files = collect_generated_typescript(temp_dir)

    assert files == {"src/user/user.controller.ts": "export class UserController {}"}
