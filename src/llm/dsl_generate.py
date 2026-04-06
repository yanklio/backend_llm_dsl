import argparse
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.prompts import SYSTEM_PROMPT
from src.llm.wrapper import GenerationResult, LLMClient
from src.shared import logger
from src.shared.utils import clean_llm_response

load_dotenv()


def natural_language_to_yaml(
    description: str, primary_model: str | None = None
) -> GenerationResult:
    """Convert natural language to YAML blueprint using LLM.

    Args:
        description (str): Plain English description of the desired NestJS application.
        primary_model (str | None): Provider ID to try first (groq, openrouter, gemini, ollama).

    Returns:
        GenerationResult: The generated YAML content and metadata.
    """
    client = LLMClient(temperature=0.1)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Create a NestJS application for: {description}"),
    ]

    result = client.generate(messages, primary_provider_id=primary_model)
    result.content = clean_llm_response(result.content)
    return result


def save_blueprint(generated_yaml: str, blueprint_file: str = "./blueprint.yaml") -> None:
    """Save the generated YAML blueprint to a file.

    Args:
        generated_yaml (str): The YAML content to save.
        blueprint_file (str): Path to save the blueprint file.
    """
    with open(blueprint_file, "w") as f:
        f.write(generated_yaml)
    logger.success(f"Blueprint saved to {blueprint_file}")


def main() -> None:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Generate NestJS application blueprint (DSL) from natural language"
    )

    parser.add_argument(
        "description",
        nargs="?",
        default="Create a NestJS application for a simple blog pages for multiple users",
        help="Description of the NestJS application to generate",
    )

    parser.add_argument(
        "-b",
        "--blueprint",
        default="./blueprint.yaml",
        help="Path where the blueprint YAML file should be saved",
    )

    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Primary model/provider to use (groq, gemini, openrouter, ollama)",
    )

    args = parser.parse_args()

    logger.start("Generating YAML blueprint from description")
    logger.info(f"Description: {args.description}")
    if args.model:
        logger.info(f"Preferred Model: {args.model}")

    try:
        result = natural_language_to_yaml(args.description, args.model)

        logger.info("=== Generation Statistics ===")
        logger.info(f"Provider: {result.provider}")
        logger.info(f"Time: {result.duration_seconds:.2f}s")
        if result.total_tokens:
            logger.info(
                f"Tokens: {result.total_tokens} (In: {result.input_tokens}, Out: {result.output_tokens})"
            )

        save_blueprint(result.content, args.blueprint)

        logger.debug("Generated Blueprint:")
        logger.debug(result.content[:200] + "..." if len(result.content) > 200 else result.content)

    except Exception as e:
        logger.error(f"Failed to generate blueprint: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
