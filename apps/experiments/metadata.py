"""Experiment identity and prompt metadata helpers."""

import hashlib
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any

from packages.llm_providers.core.client import get_default_model_name
from packages.llm_providers.core.prompts import (
    RAW_CODE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    TextualPromptVariant,
    build_textual_generation_messages,
)
from packages.llm_providers.generators.mixed_generate import MIXED_REQUEST_TEMPLATE
from packages.llm_providers.generators.raw_generate import EXPERIMENT_GENERATION_TEMPERATURE, _build_raw_prompt

PROMPT_VERSION = "full-app-scaffold-v1"
PROMPT_VERSIONS = {
    "dsl": "yaml-blueprint-v1",
    "raw": "raw-file-map-v1",
    "mixed": "mixed-blueprint-file-map-v1",
    "textual-gen-baseline": "textual-baseline-v1",
    "textual-gen-spec": "textual-spec-v1",
    "textual-gen-fewshot": "textual-fewshot-v1",
}
PROVIDER_IDS = ["gemini", "groq", "ollama", "openrouter"]
PROVIDER_MODELS = {pid: get_default_model_name(pid) for pid in PROVIDER_IDS}
PLACEHOLDER_REQUIREMENT = "<benchmark-requirement>"
PLACEHOLDER_CONTEXT = "<existing-project-context>"
PLACEHOLDER_BLUEPRINT = "<generated-blueprint-yaml>"


def short_hash(value: str, length: int = 10) -> str:
    """Return a stable short SHA-256 hash for a string value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def model_name_for_provider(provider: str) -> str:
    """Return the configured exact model name for a provider ID."""
    return PROVIDER_MODELS.get(provider, "unknown")


def prompt_version_for(approach: str) -> str:
    """Return the prompt version for an approach."""
    return PROMPT_VERSIONS[approach]


def prompt_hash_for(approach: str) -> str:
    """Return a stable hash of prompt text used by one approach."""
    prompt_text = _prompt_text_for_hash(approach)
    return short_hash(f"{prompt_version_for(approach)}\n{prompt_text}")


def _serialize_messages(messages: list[Any]) -> str:
    """Serialize actual model messages in stable order for hashing."""
    return "\n---MESSAGE---\n".join(f"{message.__class__.__name__}:\n{message.content}" for message in messages)


def _prompt_text_for_hash(approach: str) -> str:
    """Build the actual message text shape sent for one approach."""
    from langchain_core.messages import HumanMessage, SystemMessage

    if approach == "dsl":
        from packages.llm_providers.generators.dsl_generate import DSL_REQUEST_TEMPLATE

        return _serialize_messages(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=DSL_REQUEST_TEMPLATE.format(description=PLACEHOLDER_REQUIREMENT)),
            ]
        )
    if approach == "raw":
        return _serialize_messages(
            [
                SystemMessage(content=RAW_CODE_SYSTEM_PROMPT),
                HumanMessage(content=_build_raw_prompt(PLACEHOLDER_CONTEXT, PLACEHOLDER_REQUIREMENT)),
            ]
        )
    if approach == "mixed":
        return _serialize_messages(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"Create a NestJS application for: {PLACEHOLDER_REQUIREMENT}"),
                SystemMessage(content=RAW_CODE_SYSTEM_PROMPT),
                HumanMessage(
                    content=MIXED_REQUEST_TEMPLATE.format(
                        description=PLACEHOLDER_REQUIREMENT,
                        blueprint_yaml=PLACEHOLDER_BLUEPRINT,
                    )
                ),
            ]
        )
    variant_by_approach = {
        "textual-gen-baseline": TextualPromptVariant.BASELINE,
        "textual-gen-spec": TextualPromptVariant.SPEC,
        "textual-gen-fewshot": TextualPromptVariant.FEWSHOT,
    }
    return _serialize_messages(
        build_textual_generation_messages(PLACEHOLDER_REQUIREMENT, variant_by_approach[approach])
    )


def _command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def run_id_for(provider: str, approaches: list[str], created_at: str) -> str:
    """Create a readable timestamped run ID with a short identity hash."""
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d_%H%M%S")
    identity_hash = short_hash(f"{created_at}:{provider}:{','.join(approaches)}", length=8)
    return f"{timestamp}_{identity_hash}"


def build_run_metadata(
    provider: str,
    approaches: list[str],
    repetitions: int = 1,
    case_ids: list[str] | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Build metadata saved alongside every experiment run."""
    created_at = datetime.now(timezone.utc).isoformat()
    return {
        "run_id": run_id_for(provider, approaches, created_at),
        "created_at": created_at,
        "git_commit": _command_output(["git", "rev-parse", "HEAD"]),
        "working_tree_dirty": bool(_command_output(["git", "status", "--porcelain"])),
        "provider": provider,
        "model_name": model_name or model_name_for_provider(provider),
        "temperature": EXPERIMENT_GENERATION_TEMPERATURE,
        "repetitions": repetitions,
        "approaches": approaches,
        "selected_test_cases": case_ids or [],
        "prompt_versions": {approach: prompt_version_for(approach) for approach in approaches},
        "prompt_hashes": {approach: prompt_hash_for(approach) for approach in approaches},
        "python_version": platform.python_version(),
        "node_version": _command_output(["node", "--version"]),
        "npm_version": _command_output(["npm", "--version"]),
    }


def record_identity(
    *,
    provider: str,
    approach: str,
    test_case: str,
    tier: str,
    repetition: int = 1,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Build identity metadata used for result records and resume keys."""
    return {
        "provider": provider,
        "model_name": model_name or model_name_for_provider(provider),
        "approach": approach,
        "test_case": test_case,
        "tier": tier,
        "prompt_version": prompt_version_for(approach),
        "prompt_hash": prompt_hash_for(approach),
        "repetition": repetition,
    }


def resume_key(record: dict[str, Any]) -> tuple[str, ...]:
    """Return the identity tuple used to decide whether a run is already complete."""
    key = (
        record.get("test_case", ""),
        record.get("approach", ""),
        record.get("provider", ""),
        record.get("model_name", ""),
        record.get("prompt_hash", ""),
    )
    if "repetition" not in record:
        return key
    return (*key, str(record.get("repetition", "")))
