import argparse
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from packages.llm_providers import GenerationResult, LLMClient
from packages.llm_providers.core.prompts import SYSTEM_PROMPT
from packages.llm_providers.core.response_parser import clean_llm_response
from packages.llm_providers.generators.output import log_generation_statistics
from packages.shared import logger

load_dotenv()


DSL_REQUEST_TEMPLATE = "Create a NestJS application for: {description}"


def natural_language_to_yaml(
    description: str,
    provider: str = "openrouter",
    model_name: str | None = None,
) -> GenerationResult:
    """Convert natural language to YAML blueprint using LLM.

    Args:
        description (str): Plain English description of the desired NestJS application.
        provider (str): Provider to use (gemini, groq, ollama, openrouter). Default: openrouter.
        model_name (str | None): Optional exact provider model override.

    Returns:
        GenerationResult: The generated YAML content and metadata.
    """
    client = LLMClient(provider_id=provider or "openrouter", temperature=0.1, model_name=model_name)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=DSL_REQUEST_TEMPLATE.format(description=description)),
    ]

    result = client.generate(messages)
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
    parser = argparse.ArgumentParser(description="Generate NestJS application blueprint (DSL) from natural language")

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
        result = natural_language_to_yaml(args.description, provider=args.model or "openrouter")
        log_generation_statistics(result)
        save_blueprint(result.content, args.blueprint)

        logger.debug("Generated Blueprint:")
        logger.debug(result.content[:200] + "..." if len(result.content) > 200 else result.content)

    except Exception as e:
        logger.error(f"Failed to generate blueprint: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
