import argparse
import json
import traceback
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.prompts import RAW_CODE_SYSTEM_PROMPT
from src.llm.wrapper import GenerationResult, LLMClient
from src.shared import logger
from src.shared.utils import clean_llm_response, try_parse_json

load_dotenv()


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

    context = "=== EXISTING PROJECT FILES ===\n\n"

    for file_path in project_path.rglob("*.ts"):
        if "node_modules" not in str(file_path):
            try:
                rel_path = file_path.relative_to(project_path)
                content = file_path.read_text()
                context += f"\n--- {rel_path} ---\n{content}\n"
            except Exception:
                pass

    return context


def natural_language_to_code(
    description: str, project_dir: str = "./nest_project", primary_model: str | None = None
) -> GenerationResult:
    """Generate code from simple description - vibe coder style.

    Args:
        description (str): Plain English description of the desired application.
        project_dir (str): Directory path where the project files should be generated.
        primary_model (str | None): Provider ID to try first.

    Returns:
        GenerationResult: The generated code content and metadata.
    """
    existing_context = read_project_context(project_dir)
    client = LLMClient(temperature=0.2)

    user_prompt = f"""{existing_context}

=== REQUEST ===
{description}

Generate ALL files needed for a COMPLETE, WORKING NestJS application inside src/ directory.
Every file must have FULL implementation - no placeholders or TODOs.
Make it production-ready and runnable."""

    messages = [SystemMessage(content=RAW_CODE_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]

    logger.start("Generating code with LLM...")

    result = client.generate(messages, primary_provider_id=primary_model)

    try:
        cleaned_content = clean_llm_response(result.content)
        result.content = cleaned_content
        files = try_parse_json(cleaned_content)
        logger.success(f"Generated {len(files)} files via {result.provider}")
        return result
    except Exception as e:
        logger.error("Failed to parse LLM response as JSON")
        logger.error(f"Parse error: {str(e)}")

        # Save to file for debugging
        debug_file = Path("/tmp/llm_response_debug.json")
        debug_file.write_text(cleaned_content)
        logger.error(f"Saved malformed response to {debug_file}")

        logger.error("First 2000 chars of cleaned response:")
        logger.error(cleaned_content[:2000])
        logger.error("Last 500 chars of cleaned response:")
        logger.error(cleaned_content[-500:])
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")


def save_files(files: dict[str, Any], output_dir: str) -> None:
    """Save generated files to directory.

    Args:
        files (dict[str, Any]): Dictionary of file paths to content.
        output_dir (str): Base directory to save files in.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

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


def _prepare_file_content(content: Any, file_path: str) -> str:
    """Prepare file content for writing, handling JSON and escape sequences.

    Args:
        content: Raw content from JSON file map.
        file_path: File path for logging purposes.

    Returns:
        Prepared string content ready to write.
    """
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)

    if isinstance(content, str) and "\\n" in content:
        if content.count("\\n") > content.count("\n") * 2:
            logger.warn(f"Detected literal escape sequences in {file_path}, fixing...")
            content = content.replace("\\n", "\n")
            content = content.replace("\\t", "\t")
            content = content.replace('\\"', '"')
            content = content.replace("\\\\", "\\")

    return content


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
        result = natural_language_to_code(args.description, args.output, args.model)

        # Log statistics
        logger.info("=== Generation Statistics ===")
        logger.info(f"Provider: {result.provider}")
        logger.info(f"Time: {result.duration_seconds:.2f}s")
        if result.total_tokens:
            logger.info(
                f"Tokens: {result.total_tokens} (In: {result.input_tokens}, Out: {result.output_tokens})"
            )

        cleaned_content = clean_llm_response(result.content)
        files = try_parse_json(cleaned_content)
        save_files(files, args.output)

        logger.success("Done! Run with:")
        logger.info(f"  cd {args.output}")
        logger.info("  npm install")
        logger.info("  npm run start:dev")

    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
