"""LLM-based prompt-alignment evaluation for generated NestJS code."""

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import LLMClient
from src.llm.prompts import PROMPT_ALIGNMENT_SYSTEM_PROMPT
from src.llm.response_parser import clean_llm_response, try_parse_json

DEFAULT_ALIGNMENT_PROVIDER = "openrouter"
DEFAULT_ALIGNMENT_MODEL = "openai/gpt-oss-120b"
PROMPT_ALIGNMENT_VERSION = "prompt-alignment-v1"

PROMPT_ALIGNMENT_REQUEST_TEMPLATE = """=== USER REQUIREMENT ===
{requirement}

=== EXPECTED ENDPOINTS FROM TEST CASE ===
{endpoints}

=== GENERATED TYPESCRIPT FILES ===
{generated_files}

Judge only how closely the generated files implement the user requirement."""


def evaluate_prompt_alignment(
    *,
    requirement: str,
    endpoints: list[str],
    project_dir: Path,
    provider: str = DEFAULT_ALIGNMENT_PROVIDER,
    model_name: str = DEFAULT_ALIGNMENT_MODEL,
) -> dict[str, Any]:
    """Evaluate how well generated code aligns with the original prompt."""
    generated_files = collect_generated_typescript(project_dir)
    result = _generate_alignment_result(
        requirement=requirement,
        endpoints=endpoints,
        generated_files=generated_files,
        provider=provider,
        model_name=model_name,
    )
    alignment = parse_alignment_response(result.content)

    return {
        "provider": provider,
        "model_name": result.model_name or model_name,
        "prompt_version": PROMPT_ALIGNMENT_VERSION,
        "metrics": {
            "duration_seconds": result.duration_seconds,
            "input_tokens": result.input_tokens or 0,
            "output_tokens": result.output_tokens or 0,
            "total_tokens": result.total_tokens or 0,
        },
        "source_files": {
            "count": len(generated_files),
            "total_characters": sum(len(content) for content in generated_files.values()),
        },
        "result": alignment,
    }


def collect_generated_typescript(project_dir: Path) -> dict[str, str]:
    """Collect generated TypeScript source files from a Nest project."""
    source_dir = project_dir / "src"
    if not source_dir.exists():
        return {}

    files = {}
    for file_path in sorted(source_dir.rglob("*.ts")):
        if "node_modules" in file_path.parts or "dist" in file_path.parts:
            continue
        relative_path = file_path.relative_to(project_dir).as_posix()
        files[relative_path] = file_path.read_text()
    return files


def parse_alignment_response(content: str) -> dict[str, Any]:
    """Parse and normalize a prompt-alignment judge response."""
    parsed = try_parse_json(clean_llm_response(content))
    score = _normalize_alignment_score(parsed.get("alignment_score"))

    return {
        "alignment_score": score,
        "missing_requirements": _normalize_string_list(
            parsed.get("missing_requirements", [])
        ),
        "extra_features": _normalize_string_list(parsed.get("extra_features", [])),
        "rationale": str(parsed.get("rationale", "")),
    }


def _generate_alignment_result(
    *,
    requirement: str,
    endpoints: list[str],
    generated_files: dict[str, str],
    provider: str,
    model_name: str,
) -> Any:
    """Call the configured LLM judge for one prompt-alignment evaluation."""
    client = LLMClient(
        provider_id=provider,
        temperature=0.0,
        model_name=model_name,
    )
    messages = [
        SystemMessage(content=PROMPT_ALIGNMENT_SYSTEM_PROMPT),
        HumanMessage(
            content=PROMPT_ALIGNMENT_REQUEST_TEMPLATE.format(
                requirement=requirement,
                endpoints=_format_endpoints(endpoints),
                generated_files=_format_generated_files(generated_files),
            )
        ),
    ]
    return client.generate(messages)


def _format_endpoints(endpoints: list[str]) -> str:
    """Format expected endpoints for the judge prompt."""
    if not endpoints:
        return "No endpoint list provided."
    return "\n".join(f"- {endpoint}" for endpoint in endpoints)


def _format_generated_files(files: dict[str, str]) -> str:
    """Format generated source files for the judge prompt."""
    if not files:
        return "No generated TypeScript source files found."

    return "\n\n".join(
        f"--- {path} ---\n```typescript\n{content}\n```"
        for path, content in files.items()
    )


def _normalize_alignment_score(value: Any) -> int:
    """Normalize an arbitrary JSON value into the 0-5 alignment scale."""
    try:
        score = int(value)
    except (TypeError, ValueError):
        raise ValueError("alignment_score must be an integer from 0 to 5")

    if not 0 <= score <= 5:
        raise ValueError("alignment_score must be an integer from 0 to 5")
    return score


def _normalize_string_list(value: Any) -> list[str]:
    """Normalize a JSON value into a list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
