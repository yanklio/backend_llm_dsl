
import argparse
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

from src.shared import logger
from src.shared.utils import clean_llm_response
from src.llm.wrapper import LLMClient, GenerationResult

load_dotenv()

def natural_language_to_yaml(description: str, primary_model: str | None = None) -> GenerationResult:
    """Convert natural language to YAML blueprint using LLM.

    Args:
        description (str): Plain English description of the desired NestJS application.
        primary_model (str | None): Provider ID to try first (groq, openrouter, gemini, ollama).

    Returns:
        GenerationResult: The generated YAML content and metadata.
    """
    client = LLMClient(temperature=0.1)

    system_prompt = """You are a YAML blueprint generator for NestJS applications.
Don't forget about relations if needed. Don't create `id`, `createdAt` or `updatedAt` fields at all (already included).

🚨 CRITICAL STRUCTURE RULES:
1. ONE MODULE PER ENTITY - Each module represents ONE database entity
2. NEVER create separate modules for services, controllers, or repositories (e.g., NO "UserService", "UserController", "UserRepository")
3. ALWAYS include the entity definition with fields - never set entity to null
4. Module name should be the entity name in PascalCase (e.g., "User", "Post", "Product")

CORRECT structure (one module per entity):
```yaml
modules:
  - name: User
    generate: [controller, service, module, entity, dto]
    entity:
      fields:
        - name: email
          type: string
          required: true
```

WRONG (DO NOT DO THIS):
```yaml
- name: UserService    # WRONG - don't add Service suffix
  generate: [service]
  entity: null         # WRONG - always include entity
- name: UserController # WRONG - don't create separate controller module
  generate: [controller]
```

Generate ONLY valid YAML (no other text, no markdown) following this exact structure:

root:
  name: PetAdministration
  database:
    type: sqlite
    database: ./data/app.db
    synchronize: true
    logging: false

  features:
    cors: true
    swagger: true

modules:
  - name: Owner
    generate: [controller, service, module, entity, dto]
    entity:
      fields:
        - name: name
          type: string
          required: true
          validation: {minLength: 3, maxLength: 100}
        - name: age
          type: number
          required: true
          validation: {min: 0}
      relations:
        - type: OneToMany
          model: Pet
          field: pets
          description: A list of pets belonging to this owner
  - name: Pet
    generate: [controller, service, module, entity, dto]
    entity:
      fields:
        - name: name
          type: string
          required: true
          validation: {minLength: 1, maxLength: 50}
        - name: breed
          type: string
          required: false
      relations:
        - type: ManyToOne
          model: Owner
          field: owner
          description: The owner of this pet

Only respond with valid YAML. No explanations. No markdown code blocks. Just raw YAML."""

    messages = [
        SystemMessage(content=system_prompt),
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
            logger.info(f"Tokens: {result.total_tokens} (In: {result.input_tokens}, Out: {result.output_tokens})")

        save_blueprint(result.content, args.blueprint)
        
        logger.debug("Generated Blueprint:")
        logger.debug(result.content[:200] + "..." if len(result.content) > 200 else result.content)
        
    except Exception as e:
        logger.error(f"Failed to generate blueprint: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
