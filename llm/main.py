import os
import subprocess

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
messages = [
    ("system", "Translate the user sentence to French."),
    ("human", "I love programming."),
]


def natural_language_to_yaml(description: str) -> str:
    """Convert natural language to YAML blueprint using LangChain + Gemini"""

    system_prompt = """You are a YAML blueprint generator for NestJS applications.
Generate ONLY valid YAML (no other text, no markdown) following this exact structure:

root:
  name: AppName
  database:
    type: sqlite
    database: ./data/app.db
    synchronize: true
    logging: false

modules:
  - name: EntityName
    generate: [controller, service, module, entity, dto]
    entity:
      fields:
        - name: fieldName
          type: string
          required: true
          validation: {minLength: 3, maxLength: 100}
        - name: anotherField
          type: number
          required: true
          validation: {min: 0}

Only respond with valid YAML. No explanations. No markdown code blocks. Just raw YAML."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Create a NestJS application for: {description}"),
    ]

    response = llm.invoke(messages)

    # Extract text content
    yaml_text = response.content

    if "```yaml" in yaml_text:
        yaml_text = yaml_text.split("```yaml")[1].split("```")[0].strip()
    elif "```" in yaml_text:
        yaml_text = yaml_text.split("```")[1].split("```")[0].strip()

    return yaml_text


def write_blueprint_and_run(
    description: str,
    blueprint_file: str = "../blueprint.yaml",
    script_file: str = "./generate.sh",
):
    """Generate YAML blueprint, write to file, and run script"""

    # Generate the YAML blueprint
    # print(f"Generating blueprint for: {description}")
    yaml_content = natural_language_to_yaml(description)

    # # Write blueprint to file
    with open(blueprint_file, "w") as f:
        f.write(yaml_content)
    print(f"Blueprint written to {blueprint_file}")

    # Check if script exists and run it
    if os.path.exists(script_file):
        print(f"Running script: {script_file}")
        try:
            result = subprocess.run(
                ["./generate.sh"], shell=True, capture_output=True, text=True, cwd=".."
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
        print(f"Script file {script_file} not found. Only blueprint was generated.")

    return ""  # yaml_content


# Example usage
if __name__ == "__main__":
    description = "Create a NestJS application for a simple blog pages for multiple users"

    # Generate, write, and run
    blueprint = write_blueprint_and_run(description)

    # Also print the generated blueprint for reference
    print("\nGenerated Blueprint:")
    print(blueprint)
