import argparse
import sys
import traceback
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import GenerationResult, LLMClient
from src.llm.output import (
    log_generation_statistics,
    log_json_parse_failure,
    log_run_instructions,
    parse_generated_files,
    save_generated_files,
)
from src.llm.prompts import RAW_CODE_SYSTEM_PROMPT
from src.shared import logger

load_dotenv()


PROJECT_CONTEXT_HEADER = "=== EXISTING PROJECT FILES ===\n\n"
RAW_REQUEST_TEMPLATE = """{existing_context}

=== REQUEST ===
{description}

Generate ALL files needed for a COMPLETE, WORKING NestJS application inside src/ directory.
Include root bootstrap files `src/main.ts` and `src/app.module.ts`.
Configure the app so `npm run build` and `npm run start` can work in the provided Nest scaffold.
Every file must have FULL implementation - no placeholders or TODOs.
Make it production-ready and runnable."""


def read_project_context(project_dir: str) -> str:
    """Read existing project files for context.

    Args:
        project_dir (str): Path to the project directory.

    Returns:
        str: Concatenated content of all TypeScript files in the project.
    """
    project_path = Path(project_dir)

    if not project_path.exists():
        return "No existing project found."

    context_parts = [PROJECT_CONTEXT_HEADER]

    for file_path in project_path.rglob("*.ts"):
        if "node_modules" in str(file_path):
            continue
        file_context = _read_typescript_context_file(project_path, file_path)
        if file_context is not None:
            context_parts.append(file_context)

    return "".join(context_parts)


def _read_typescript_context_file(project_path: Path, file_path: Path) -> str | None:
    """Read one TypeScript file for inclusion in the raw-generation prompt."""
    try:
        relative_path = file_path.relative_to(project_path)
        return f"\n--- {relative_path} ---\n{file_path.read_text()}\n"
    except Exception:
        return None


def _build_raw_prompt(existing_context: str, description: str) -> str:
    """Build the user prompt for raw code generation."""
    return RAW_REQUEST_TEMPLATE.format(
        existing_context=existing_context,
        description=description,
    )


def generate_code_files(
    description: str,
    project_dir: str = "./nest_project",
    provider: str = "openrouter",
) -> tuple[GenerationResult, dict[str, Any]]:
    """Generate and parse a complete NestJS file map from natural language."""
    existing_context = read_project_context(project_dir)
    client = LLMClient(provider_id=provider, temperature=0.2)

    messages = [
        SystemMessage(content=RAW_CODE_SYSTEM_PROMPT),
        HumanMessage(content=_build_raw_prompt(existing_context, description)),
    ]

    logger.start("Generating code with LLM...")
    result = client.generate(messages)

    try:
        result, files = parse_generated_files(result)
        logger.success(f"Generated {len(files)} files via {result.provider}")
        return result, files
    except Exception as e:
        log_json_parse_failure(result.content, e)
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")


def natural_language_to_code(
    description: str, project_dir: str = "./nest_project", provider: str = "openrouter"
) -> GenerationResult:
    """Generate code from simple description - vibe coder style.

    Args:
        description (str): Plain English description of the desired application.
        project_dir (str): Directory path where the project files should be generated.
        provider (str): Provider to use (gemini, groq, ollama, openrouter). Default: openrouter.

    Returns:
        GenerationResult: The generated code content and metadata.
    """
    result, _ = generate_code_files(description, project_dir, provider)
    return result


def save_files(files: dict[str, Any], output_dir: str) -> None:
    """Save generated files to directory.

    Args:
        files (dict[str, Any]): Dictionary of file paths to content.
        output_dir (str): Base directory to save files in.
    """
    save_generated_files(files, output_dir)


def main() -> None:
    """Main execution entry point."""
    parser = argparse.ArgumentParser(
        description="Vibe coder - generate NestJS code from simple descriptions"
    )

    parser.add_argument(
        "description",
        help="What you want (e.g., 'add a Post entity with title and content')",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./nest_project",
        help="Output directory (default: ./nest_project)",
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
        result, files = generate_code_files(args.description, args.output, args.model)
        log_generation_statistics(result)
        save_files(files, args.output)
        log_run_instructions(args.output)

    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
