
import argparse
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared import logger
from src.shared.utils import clean_llm_response
from src.llm.wrapper import LLMClient, GenerationResult

load_dotenv()

def natural_language_to_yaml(description: str, primary_model: str = None) -> GenerationResult:
    """Convert natural language to YAML blueprint using LLM."""
    
    client = LLMClient(temperature=0.1)

    system_prompt = """You are a YAML blueprint generator for NestJS applications.
Don't forget about relations if needed. Don't create `id`, `createdAt` or `updatedAt` fields at all (already included).

🚨 CRITICAL NAMING RULE:
- Module names MUST be singular entity names WITHOUT any suffix
- ✓ CORRECT: "User", "Post", "Product", "Category", "Order"
- ✗ WRONG: "UserModule", "PostModule", "ProductModule", "Users", "user"
- The name field should be the entity name in PascalCase (e.g., "User" not "UserModule")
- DO NOT add "Module", "Service", "Controller" or any other suffix to the module name

Generate ONLY valid YAML (no other text, no markdown) following this exact structure (this is only an example, adapt it based on prompt needs):

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


def save_blueprint(generated_yaml: str, blueprint_file: str = "./blueprint.yaml"):
    """Save the generated YAML blueprint to a file."""
    with open(blueprint_file, "w") as f:
        f.write(generated_yaml)
    logger.success(f"Blueprint saved to {blueprint_file}")


def main():
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
