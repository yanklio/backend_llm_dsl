"""Mixed approach: Blueprint + Raw code generation.

Two-phase approach:
1. Generate YAML blueprint from natural language
2. Use blueprint as additional context to generate raw code
"""

import argparse
import json
import traceback
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.dsl_generate import natural_language_to_yaml, save_blueprint
from src.llm.prompts import RAW_CODE_SYSTEM_PROMPT
from src.llm.wrapper import GenerationResult, LLMClient
from src.shared import logger
from src.shared.utils import clean_llm_response, try_parse_json
from src.dsl.generate import main as dsl_generate

load_dotenv()


def _create_mixed_prompt(blueprint_yaml: str, description: str) -> str:
    """Create a user prompt that includes both the description and blueprint.

    Args:
        blueprint_yaml (str): The generated YAML blueprint.
        description (str): Original natural language description.

    Returns:
        str: Combined prompt for raw code generation.
    """
    return f"""=== NATURAL LANGUAGE REQUEST ===
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


def mixed_generate(
    description: str,
    output_dir: str = "./nest_project",
    blueprint_path: str = "./mixed_blueprint.yaml",
    primary_model: str | None = None,
) -> dict[str, Any]:
    """Generate NestJS code using the mixed approach.

    Phase 1: Generate YAML blueprint from description
    Phase 2: Use blueprint as context for raw code generation

    Args:
        description (str): Natural language description of desired application.
        output_dir (str): Directory to save generated files.
        blueprint_path (str): Path to save the intermediate blueprint.
        primary_model (str | None): Preferred LLM provider.

    Returns:
        dict[str, Any]: Dictionary with generation results and statistics.
    """
    logger.start("Phase 1: Generating blueprint from description...")

    blueprint_result = natural_language_to_yaml(description, primary_model)
    blueprint_yaml = blueprint_result.content

    save_blueprint(blueprint_yaml, blueprint_path)
    logger.info(f"Phase 1 complete: {blueprint_result.duration_seconds:.2f}s")

    logger.start("Phase 2: Generating code with blueprint context...")

    client = LLMClient(temperature=0.2)

    user_prompt = _create_mixed_prompt(blueprint_yaml, description)
    messages = [SystemMessage(content=RAW_CODE_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

    code_result = client.generate(messages, primary_provider_id=primary_model)
    logger.info(f"Phase 2 complete: {code_result.duration_seconds:.2f}s")

    try:
        cleaned_content = clean_llm_response(code_result.content)
        files = try_parse_json(cleaned_content)

        total_duration = blueprint_result.duration_seconds + code_result.duration_seconds
        total_tokens = (blueprint_result.total_tokens or 0) + (code_result.total_tokens or 0)

        return {
            "success": True,
            "files": files,
            "blueprint": blueprint_yaml,
            "statistics": {
                "total_duration_seconds": total_duration,
                "phase1_duration": blueprint_result.duration_seconds,
                "phase2_duration": code_result.duration_seconds,
                "total_tokens": total_tokens,
                "phase1_tokens": blueprint_result.input_tokens,
                "phase2_tokens": code_result.total_tokens,
                "provider": code_result.provider,
            },
        }
    except Exception as e:
        logger.error(f"Phase 2 failed to parse code: {e}")
        return {
            "success": False,
            "error": str(e),
            "blueprint": blueprint_yaml,
            "phase1_result": blueprint_result,
        }


def save_mixed_files(files: dict[str, Any], output_dir: str) -> int:
    """Save generated files to directory.

    Args:
        files (dict[str, Any]): Dictionary of file paths to content.
        output_dir (str): Base directory to save files in.

    Returns:
        int: Number of files saved.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    from src.llm.raw_generate import _prepare_file_content

    logger.start(f"Saving files to {output_dir}...")

    saved_count = 0
    for file_path, content in files.items():
        try:
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            content = _prepare_file_content(content, file_path)

            full_path.write_text(content, encoding="utf-8")
            logger.success(f"Saved {file_path}")
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")

    logger.end(f"Saved {saved_count}/{len(files)} files")
    return saved_count


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
            logger.info("=== Generation Statistics ===")
            logger.info(f"Total time: {stats['total_duration_seconds']:.2f}s")
            logger.info(f"  Phase 1 (blueprint): {stats['phase1_duration']:.2f}s")
            logger.info(f"  Phase 2 (code): {stats['phase2_duration']:.2f}s")
            if stats["total_tokens"]:
                logger.info(f"Total tokens: {stats['total_tokens']}")

            save_mixed_files(result["files"], args.output)

            logger.success("Done! Run with:")
            logger.info(f"  cd {args.output}")
            logger.info("  npm install")
            logger.info("  npm run start:dev")
        else:
            logger.error(f"Generation failed: {result.get('error')}")
            logger.info(f"Blueprint saved to: {args.blueprint}")

    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()