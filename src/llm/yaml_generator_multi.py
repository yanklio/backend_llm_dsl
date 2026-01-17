"""
Multi-Provider YAML Generator
Supports multiple LLM providers with automatic fallback to avoid rate limits
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.shared import logger

load_dotenv()


class MultiProviderYAMLGenerator:
    """YAML generator with support for multiple LLM providers"""

    def __init__(self):
        self.providers = []
        self._setup_providers()

    def _setup_providers(self):
        """Setup providers based on availability (Groq → OpenRouter → Gemini)"""

        if os.getenv("GROQ_API_KEY"):
            try:
                from langchain_groq import ChatGroq

                self.providers.append(
                    {
                        "name": "Groq (Llama 3.1)",
                        "llm": ChatGroq(
                            model="llama-3.1-8b-instant",
                            api_key=os.getenv("GROQ_API_KEY"),
                            temperature=0.1,
                        ),
                    }
                )
                logger.info("✓ Groq provider configured")
            except Exception as e:
                logger.warn(f"Groq setup failed: {e}")

        if os.getenv("OPENROUTER_API_KEY"):
            try:
                from langchain_openai import ChatOpenAI

                self.providers.append(
                    {
                        "name": "OpenRouter (Gemini Free)",
                        "llm": ChatOpenAI(
                            model="google/gemini-2.0-flash-exp:free",
                            api_key=os.getenv("OPENROUTER_API_KEY"),
                            base_url="https://openrouter.ai/api/v1",
                            temperature=0.1,
                        ),
                    }
                )
                logger.info("✓ OpenRouter provider configured")
            except Exception as e:
                logger.warn(f"OpenRouter setup failed: {e}")

        if os.getenv("GOOGLE_API_KEY"):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self.providers.append(
                    {
                        "name": "Google Gemini",
                        "llm": ChatGoogleGenerativeAI(
                            model="gemini-2.0-flash-exp", temperature=0.1
                        ),
                    }
                )
                logger.info("✓ Google Gemini provider configured")
            except Exception as e:
                logger.warn(f"Gemini setup failed: {e}")

        try:
            from langchain_ollama import ChatOllama
            import requests

            try:
                requests.get("http://localhost:11434", timeout=1)
                self.providers.append(
                    {
                        "name": "Ollama (Local)",
                        "llm": ChatOllama(model="llama3.1", temperature=0.1),
                    }
                )
                logger.info("✓ Ollama (local) provider configured")
            except:
                pass  # Ollama not running
        except Exception:
            pass  # Ollama not installed

        if not self.providers:
            logger.error("❌ No LLM providers configured!")
            logger.info("Please set one of these environment variables:")
            logger.info("  - GROQ_API_KEY (recommended - 30 req/min)")
            logger.info("  - OPENROUTER_API_KEY (20 req/min)")
            logger.info("  - GOOGLE_API_KEY (5 req/min)")
            logger.info("Or install Ollama locally")
            sys.exit(1)

        logger.success(f"Configured {len(self.providers)} LLM provider(s)")

    def generate_yaml(self, description: str) -> str:
        """Generate YAML using available providers with automatic fallback"""

        system_prompt = """You are a YAML blueprint generator for NestJS applications.
Generate ONLY valid YAML (no other text, no markdown) following this exact structure:
Don't forget about relations if needed. Don't create `CreatedAt` or `UpdatedAt` fields at all (already included).

root:
  name: AppName
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

        # Try each provider in order
        for i, provider in enumerate(self.providers):
            try:
                logger.info(f"Trying provider: {provider['name']}")
                response = provider["llm"].invoke(messages)
                yaml_text = response.content

                # Clean up any markdown code blocks if present
                if "```yaml" in yaml_text:
                    yaml_text = yaml_text.split("```yaml")[1].split("```")[0].strip()
                elif "```" in yaml_text:
                    yaml_text = yaml_text.split("```")[1].split("```")[0].strip()

                logger.success(f"✓ Generated YAML using {provider['name']}")
                return yaml_text

            except Exception as e:
                logger.warning(f"✗ {provider['name']} failed: {e}")
                if i < len(self.providers) - 1:
                    logger.info(f"Trying next provider...")
                else:
                    logger.error("All providers failed!")
                    raise

        raise Exception("No providers available")


def natural_language_to_yaml(description: str) -> str:
    """Convert natural language to YAML blueprint using multi-provider approach"""
    generator = MultiProviderYAMLGenerator()
    return generator.generate_yaml(description)


def save_blueprint(
    generated_yaml: str,
    blueprint_file: str = "./blueprint.yaml",
):
    """Save the generated YAML blueprint to a file"""
    with open(blueprint_file, "w") as f:
        f.write(generated_yaml)
    logger.success(f"Blueprint saved to {blueprint_file}")
    return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate NestJS application from natural language description"
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

    args = parser.parse_args()

    logger.start("Generating YAML blueprint from description")
    logger.info(f"Description: {args.description}")

    blueprint = natural_language_to_yaml(args.description)
    save_blueprint(blueprint, args.blueprint)

    logger.success("Blueprint generated successfully")
