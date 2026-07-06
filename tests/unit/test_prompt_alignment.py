"""Tests for prompt-alignment judging helpers."""

import pytest

from packages.llm_providers.core.prompts import PROMPT_ALIGNMENT_SYSTEM_PROMPT
from packages.llm_providers.evaluation.prompt_alignment import (
    PROMPT_ALIGNMENT_VERSION,
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


def test_prompt_alignment_v2_calibrates_middle_scores() -> None:
    """Judge prompt should distinguish near-misses from broad omissions."""
    assert PROMPT_ALIGNMENT_VERSION == "prompt-alignment-v2"
    assert "Do not give 3 automatically" in PROMPT_ALIGNMENT_SYSTEM_PROMPT
    assert "Use 4 for near-misses and 2 for broad/incomplete implementations" in PROMPT_ALIGNMENT_SYSTEM_PROMPT
    assert "validator import but the decorator is not applied" in PROMPT_ALIGNMENT_SYSTEM_PROMPT


def test_collect_generated_typescript_reads_src_files(temp_dir) -> None:
    """It should collect generated TypeScript files relative to the project root."""
    source_dir = temp_dir / "src" / "user"
    source_dir.mkdir(parents=True)
    (source_dir / "user.controller.ts").write_text("export class UserController {}")
    (temp_dir / "src" / "README.md").write_text("ignored")

    files = collect_generated_typescript(temp_dir)

    assert files == {"src/user/user.controller.ts": "export class UserController {}"}
