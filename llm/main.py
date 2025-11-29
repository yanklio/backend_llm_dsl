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


def write_blueprint_and_run(
    description: str,
    blueprint_file: str = "./blueprint.yaml",
    script_file: str = "./generate.sh",
):
    """Generate YAML blueprint, write to file, and run script"""
    
    yaml_content = natural_language_to_yaml(description)

    with open(blueprint_file, "w") as f:
        f.write(yaml_content)
    print(f"Blueprint written to {blueprint_file}")

    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generate.sh")
    
    if os.path.exists(script_path):
        print(f"Running script: {script_path}")
        try:
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result = subprocess.run(
                ["bash", "generate.sh"], capture_output=True, text=True, cwd=parent_dir
            )
            if result.returncode == 0:
                print("Script executed successfully!")
                if result.stdout:
                    print("Output:", result.stdout)
            else:
                print(f"Script failed with return code {result.returncode}")
                if result.stderr:
                    print("Error:", result.stderr)
        except Exception as e:
            print(f"Error running script: {e}")
    else:
        print(f"Script file {script_path} not found. Only blueprint was generated.")

    return ""  # yaml_content


if __name__ == "__main__":
    description = "Create a NestJS application for a simple blog pages for multiple users"

    blueprint = write_blueprint_and_run(description)

    print("\nGenerated Blueprint:")
    print(blueprint)
