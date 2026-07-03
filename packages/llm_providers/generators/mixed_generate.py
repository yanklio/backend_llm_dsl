"""Mixed approach: Blueprint + Raw code generation.

Two-phase approach:
1. Generate YAML blueprint from natural language
2. Use blueprint as additional context to generate raw code
"""

import argparse
import traceback
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from packages.llm_providers import LLMClient
from packages.llm_providers.core.prompts import RAW_CODE_SYSTEM_PROMPT
from packages.llm_providers.core.response_parser import clean_llm_response, try_parse_json
from packages.llm_providers.generators.dsl_generate import natural_language_to_yaml, save_blueprint
from packages.llm_providers.generators.file_writer import save_generated_files
from packages.llm_providers.generators.output import (
    log_json_parse_failure,
    log_run_instructions,
)
from packages.llm_providers.generators.raw_generate import EXPERIMENT_GENERATION_TEMPERATURE
from packages.shared import logger

load_dotenv()


@dataclass(frozen=True)
class TokenUsage:
    """Normalized token usage values for one LLM generation phase."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


def _token_usage(result: Any) -> TokenUsage:
    """Normalize nullable provider token fields into integers."""
    return TokenUsage(
        input_tokens=result.input_tokens or 0,
        output_tokens=result.output_tokens or 0,
        total_tokens=result.total_tokens or 0,
    )


MIXED_REQUEST_TEMPLATE = """=== NATURAL LANGUAGE REQUEST ===
{description}

=== GENERATED BLUEPRINT (use this structure) ===
{blueprint_yaml}

=== TASK ===
Generate the COMPLETE NestJS application code following the blueprint above.
Use the blueprint as the source of truth for:
- Entity definitions (fields, types, validations)
- Database relationships (OneToMany, ManyToOne, etc.)
- Module structure and naming

Return a SINGLE VALID JSON object mapping file paths to file content.
Keys are file paths (e.g., "src/user/user.entity.ts")
Values are the FULL FILE CONTENT as properly escaped JSON strings.
Newlines must be represented as \\n, double quotes as \\".

    Only generate .ts source files in src/ directory."""


def _create_mixed_prompt(blueprint_yaml: str, description: str) -> str:
    """Create a user prompt that includes both the description and blueprint.

    Args:
        blueprint_yaml (str): The generated YAML blueprint.
        description (str): Original natural language description.

    Returns:
        str: Combined prompt for raw code generation.
    """
    return MIXED_REQUEST_TEMPLATE.format(
        blueprint_yaml=blueprint_yaml,
        description=description,
    )


def _build_mixed_statistics(blueprint_result: Any, code_result: Any) -> dict[str, Any]:
    """Build the mixed-generation statistics payload."""
    phase1_tokens = _token_usage(blueprint_result)
    phase2_tokens = _token_usage(code_result)

    return {
        "phase1_duration": blueprint_result.duration_seconds,
        "phase2_duration": code_result.duration_seconds,
        "total_duration_seconds": blueprint_result.duration_seconds + code_result.duration_seconds,
        "phase1_input_tokens": phase1_tokens.input_tokens,
        "phase1_output_tokens": phase1_tokens.output_tokens,
        "phase1_total_tokens": phase1_tokens.total_tokens,
        "phase2_input_tokens": phase2_tokens.input_tokens,
        "phase2_output_tokens": phase2_tokens.output_tokens,
        "phase2_total_tokens": phase2_tokens.total_tokens,
        "input_tokens": phase1_tokens.input_tokens + phase2_tokens.input_tokens,
        "output_tokens": phase1_tokens.output_tokens + phase2_tokens.output_tokens,
        "total_tokens": phase1_tokens.total_tokens + phase2_tokens.total_tokens,
        "provider": code_result.provider,
        "model_name": getattr(code_result, "model_name", None),
    }


def _log_mixed_statistics(stats: dict[str, Any]) -> None:
    """Log the mixed-generation phase timings and token counts."""
    logger.info("=== Generation Statistics ===")
    logger.info(f"Total time: {stats['total_duration_seconds']:.2f}s")
    logger.info(f"  Phase 1 (blueprint): {stats['phase1_duration']:.2f}s")
    logger.info(f"  Phase 2 (code): {stats['phase2_duration']:.2f}s")
    if stats["total_tokens"]:
        logger.info(f"Total tokens: {stats['total_tokens']}")


def mixed_generate(
    description: str,
    output_dir: str = "./nest_project",
    blueprint_path: str = "./mixed_blueprint.yaml",
    primary_model: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Generate NestJS code using the mixed approach.

    Phase 1: Generate YAML blueprint from description
    Phase 2: Use blueprint as context for raw code generation

    Args:
        description (str): Natural language description of desired application.
        output_dir (str): Directory to save generated files.
        blueprint_path (str): Path to save the intermediate blueprint.
        primary_model (str | None): Preferred LLM provider.
        provider (str | None): Provider ID override; preferred over primary_model.
        model_name (str | None): Optional exact provider model override.

    Returns:
        dict[str, Any]: Dictionary with generation results and statistics.
    """
    logger.start("Phase 1: Generating blueprint from description...")

    provider_id = provider or primary_model or "openrouter"
    blueprint_result = natural_language_to_yaml(description, provider=provider_id, model_name=model_name)
    blueprint_yaml = blueprint_result.content

    save_blueprint(blueprint_yaml, blueprint_path)
    logger.info(f"Phase 1 complete: {blueprint_result.duration_seconds:.2f}s")

    logger.start("Phase 2: Generating code with blueprint context...")

    client = LLMClient(
        provider_id=provider_id,
        temperature=EXPERIMENT_GENERATION_TEMPERATURE,
        model_name=model_name,
    )

    user_prompt = _create_mixed_prompt(blueprint_yaml, description)
    messages = [SystemMessage(content=RAW_CODE_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

    code_result = client.generate(messages)
    logger.info(f"Phase 2 complete: {code_result.duration_seconds:.2f}s")

    try:
        cleaned_content = clean_llm_response(code_result.content)
        files = try_parse_json(cleaned_content)

        return {
            "success": True,
            "files": files,
            "blueprint": blueprint_yaml,
            "phase1_raw_response": blueprint_result.raw_content or blueprint_yaml,
            "code_response": code_result.raw_content or code_result.content,
            "cleaned_code_response": cleaned_content,
            "statistics": _build_mixed_statistics(blueprint_result, code_result),
        }
    except Exception as e:
        logger.error(f"Phase 2 failed to parse code: {e}")
        log_json_parse_failure(cleaned_content, e)
        return {
            "success": False,
            "error": str(e),
            "blueprint": blueprint_yaml,
            "phase1_raw_response": blueprint_result.raw_content or blueprint_yaml,
            "code_response": code_result.raw_content or code_result.content,
            "cleaned_code_response": cleaned_content,
            "phase1_result": blueprint_result,
            "statistics": _build_mixed_statistics(blueprint_result, code_result),
        }


def save_mixed_files(files: dict[str, Any], output_dir: str) -> int:
    """Save generated files to directory.

    Args:
        files (dict[str, Any]): Dictionary of file paths to content.
        output_dir (str): Base directory to save files in.

    Returns:
        int: Number of files saved.
    """
    return save_generated_files(files, output_dir)


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Mixed approach: Generate blueprint first, then code with blueprint context"
    )

    parser.add_argument(
        "description",
        help="What you want (e.g., 'create a blog with users and posts')",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./nest_project",
        help="Output directory (default: ./nest_project)",
    )

    parser.add_argument(
        "-b",
        "--blueprint",
        default="./mixed_blueprint.yaml",
        help="Path to save intermediate blueprint (default: ./mixed_blueprint.yaml)",
    )

    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Primary model/provider to use (groq, gemini, openrouter, ollama)",
    )

    args = parser.parse_args()

    if args.model:
        logger.info(f"Preferred Model: {args.model}")

    try:
        result = mixed_generate(
            description=args.description,
            output_dir=args.output,
            blueprint_path=args.blueprint,
            primary_model=args.model,
        )

        if result["success"]:
            stats = result["statistics"]
            _log_mixed_statistics(stats)
            save_mixed_files(result["files"], args.output)
            log_run_instructions(args.output)
        else:
            logger.error(f"Generation failed: {result.get('error')}")
            logger.info(f"Blueprint saved to: {args.blueprint}")

    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
