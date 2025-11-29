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


print(
    natural_language_to_yaml(
        "Create a NestJS application for a simple blog pages for multiple users"
    )
)
