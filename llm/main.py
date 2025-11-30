import argparse
import os
import subprocess

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)


def natural_language_to_yaml(description: str) -> str:
    """Convert natural language to YAML blueprint using LangChain + Gemini"""

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

    response = llm.invoke(messages)
    yaml_text = response.content
    
    return yaml_text


def save_blueprint(
    generated_yaml: str,
    blueprint_file: str = "./blueprint.yaml",
):
    """Save the generated YAML blueprint to a file"""
  
    with open(blueprint_file, "w") as f:
        f.write(generated_yaml)
    print(f"Blueprint written to {blueprint_file}")

    return ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate NestJS application from natural language description")
    
    # First argument (positional) - description
    parser.add_argument(
        "description", 
        nargs="?", 
        default="Create a NestJS application for a simple blog pages for multiple users",
        help="Description of the NestJS application to generate (default: blog application)"
    )
    
    # Flag for blueprint file path
    parser.add_argument(
        "-b", "--blueprint", 
        default="./blueprint.yaml",
        help="Path where the blueprint YAML file should be saved (default: ./blueprint.yaml)"
    )
    
    args = parser.parse_args()
    
    print(f"Description: {args.description}")
    print(f"Blueprint file: {args.blueprint}")

    blueprint = natural_language_to_yaml(args.description)
    save_blueprint(blueprint, args.blueprint)

    print("\nGenerated Blueprint:")
    print(blueprint)
