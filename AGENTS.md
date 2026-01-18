# AGENTS.md - AI Agent Documentation

This document provides a comprehensive overview of the NestJS Code Generation project for AI agents and future contributors.

## 👨‍💻 Code Style & Standards

To maintain a high-quality unified codebase, all Python code must adhere to the following standards. The project is configured with `pyproject.toml` to enforce these rules via **Ruff**.

### 1. Style Guide
*   **Formatter**: Use **Ruff** for strict formatting (black-compatible).
*   **Indent**: 4 spaces.
*   **Quotes**: Double quotes (`"`) for strings.
*   **Line Length**: 88 characters.

### 2. Imports
*   **Sorting**: Imports must be sorted and grouped in the following order:
    1.  Standard Library (e.g., `sys`, `pathlib`)
    2.  Third-Party Libraries (e.g., `yaml`, `jinja2`)
    3.  Local Application Imports (e.g., `src.shared`, `src.dsl`)
*   **Absolute Imports**: Prefer absolute imports for project modules over relative ones where possible, though relative imports are used in `__init__.py` or internal module references.
*   **Unused Imports**: Remove all unused imports.

### 3. Type Hinting
*   **Strict Typing**: All function signatures (arguments and return types) must be type-hinted.
*   **Generic Types**: Use `List`, `Dict`, `Optional`, `Any` from `typing` module for complex types.

### 4. Documentation
*   **Docstrings**: All public modules, classes, and functions must have docstrings.
*   **Format**: Use **Google-style** docstrings.
    ```python
    def my_function(param1: int, param2: str) -> bool:
        """Description of what the function does.

        Args:
            param1 (int): The first parameter.
            param2 (str): The second parameter.

        Returns:
            bool: The return value description.
        """
    ```

### 5. Linting & Validation
Run the standard linter before committing:
```bash
ruff check .
ruff format .
```

## 🎯 Project Overview

This is an **AI-powered NestJS application generator** that transforms natural language descriptions into fully functional backend applications. The system combines Large Language Models (LLMs) with Domain-Specific Language (DSL) templates to automate the creation of REST APIs with TypeORM database integration.

### Core Value Proposition
- **Natural Language to Code**: Describe your application in plain English, get production-ready NestJS code
- **Template-Driven**: Jinja2-based templates ensure consistent, maintainable code patterns
- **Full-Stack Generation**: Creates controllers, services, entities, DTOs, and modules
- **Database Integration**: Automatic TypeORM entity generation with relations

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Natural       │    │      YAML       │    │    Generated    │
│   Language      │───▶│    Blueprint    │───▶│   NestJS App    │
│   Description   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │                        │                        │
     LLM AI                 DSL Engine              NestJS Framework
   (Gemini 2.5)          (Jinja2 Templates)        (TypeScript)
```

## 📁 Project Structure

```
Practice/
├── 🤖 src/
│   ├── dsl/                  # Code Generation Engine
│   │   ├── core/             # Core generation logic
│   │   ├── templates/        # Jinja2 Templates
│   │   ├── utils/            # Utility functions
│   │   └── generate.py       # Main DSL generator entry
│   ├── llm/                  # AI/LLM Integration Layer
│   │   ├── raw_generate.py   # Direct Code Generation (Vibe Coding)
│   │   ├── dsl_generate.py   # Natural Language to YAML (Multi-Provider)
│   │   └── wrapper/          # LLM Provider Abstraction
│   │       ├── llm_client.py # Multi-provider client with fallback
│   │       └── providers/    # Individual provider implementations
│   ├── shared/               # Shared utilities (logging, etc.)
│   └── validators/           # Verification & Testing Tools
│       ├── runtime_validators/   # NPM & Runtime Checks
│       ├── syntactic_validators/ # TypeScript Syntax Checks
│       ├── shared/               # Shared validator utilities
│       └── main.py              # Main validation entry point
├── 🧪 tests/                 # Testing Suite
│   ├── test_cases/           # Scenario definitions & blueprints
│   ├── test_single_case.py   # Single case test runner
│   ├── utils:/init_nest_project.py  # Test environment setup
│   └── metrics_collector.py  # Performance metrics
├── 🏃 nest_project/          # Generated NestJS Application
├── 📄 pyproject.toml         # Python Tooling Config (Ruff)
└── 📦 requirements.txt       # Dependencies
```

## 🔄 Workflow Process

### 1. Natural Language Processing (LLM Phase)
- **Input**: Plain English description of desired application
- **Process**: Multi-provider LLM (Groq/OpenRouter/Gemini/Ollama) converts description to structured YAML
- **Output**: Raw LLM response with potential formatting issues

### 2. State Machine Repair (Sanitization Phase)
- **Input**: Raw LLM response (may contain markdown blocks, malformed JSON/YAML)
- **Process**: 
  - `clean_llm_response()`: Removes markdown code blocks (```yaml, ```json)
  - `try_parse_json()`: Fixes common LLM errors:
    - Unescaped newlines and quotes in strings
    - Missing closing braces
    - Control character escaping
- **Output**: Clean, valid YAML blueprint

### 3. Blueprint Validation (AI Phase)
```python
# Example: "Create a blog with users and posts"
description = "Create a blog application with users who can write posts"
result = natural_language_to_yaml(description)
clean_yaml = result.content  # Already sanitized
# Generates YAML with User and Post entities
```

### 4. Graph-based Relation Inference (DSL Phase)
- **Input**: YAML blueprint with entity relations
- **Process**: `handle_relations()` function:
  1. Creates relation graph: `{(Entity1, Entity2): relation_data}`
  2. Validates all referenced entities exist
  3. Detects bidirectional relations by checking reverse edges
  4. Automatically infers `inverseField` for bidirectional relations
  5. Example: If User→Post and Post→User both exist, infers inverse fields
- **Output**: Validated relations map with inverse field mappings

### 5. Code Generation (Template Rendering Phase)
- **Input**: Validated YAML blueprint with complete relation data
- **Process**: Jinja2 templates render TypeScript/NestJS code
- **Output**: Complete NestJS application structure

## 📝 Blueprint Schema

The YAML blueprint follows this structure:

```yaml
root:
  name: AppName                    # Application name
  database:                       # Database configuration
    type: sqlite                  # Database type
    database: ./data/app.db       # Database file path
    synchronize: true             # Auto-sync schema
    logging: false                # SQL logging
  features:                       # Feature flags
    cors: true                    # Enable CORS
    swagger: true                 # Enable API docs

modules:                          # Entity modules
  - name: User                    # Module name
    generate: [controller, service, module, entity, dto]
    entity:
      fields:                     # Entity fields
        - name: email
          type: string
          required: true
          validation: {isEmail: true}
        - name: name
          type: string
          required: true
          validation: {minLength: 2, maxLength: 50}
      relations:                  # Database relations
        - type: OneToMany
          model: Post
          field: posts
          description: User's blog posts
```

## 🤖 AI Integration Details

### LLM Configuration
- **Architecture**: Multi-provider with automatic fallback
- **Supported Providers**: 
  1. Groq (Primary - fastest)
  2. OpenRouter (Fallback)
  3. Google Gemini 2.5 Flash (Fallback)
  4. Ollama (Local fallback)
- **Temperature**: 0.1 (low for consistent output)
- **Framework**: LangChain with provider-specific implementations
- **Environment Variables**: 
  - `GROQ_API_KEY` (recommended)
  - `OPENROUTER_API_KEY` (optional)
  - `GOOGLE_API_KEY` (optional)
  - Ollama local installation (optional)

### Prompt Engineering
The system uses a carefully crafted system prompt that:
- Enforces strict YAML output format
- Includes entity relationship modeling
- Excludes automatic timestamp fields (handled by templates)
- Provides examples for consistent structure

## 🔧 Code Generation Templates

### Template Features
- **Entity Generation**: TypeORM decorators, field validation, relations
- **DTO Generation**: Class-validator decorators, Swagger documentation
- **Controller Generation**: CRUD endpoints, HTTP status codes, route guards
- **Service Generation**: Repository pattern, business logic, error handling
- **Module Generation**: Dependency injection, imports/exports

### Template Variables
Templates receive these data structures:
```python
template_data = {
    "module": "User",              # Module name
    "entity": {                    # Entity configuration
        "fields": [...],           # Field definitions
        "relations": [...]         # Relationship definitions
    },
    "authProtected": False         # Authentication requirement
}
```

## 🛠️ Usage Instructions

### For AI Agents

1. **Generate from Natural Language**:
```bash
# Use default provider (tries Groq first, then falls back)
python src/llm/dsl_generate.py "Create an e-commerce API with products, customers, and orders"

# Specify preferred provider
python src/llm/dsl_generate.py "Create a blog API" --model gemini
```

2. **Use Existing Blueprint**:
```bash
python src/dsl/generate.py blueprint.yaml ./nest_project
```

3. **Run Generated Application**:
```bash
cd nest_project
npm install
npm run start:dev
```

### For Developers

1. **Modify Templates**: Edit files in `dsl/templates/` to change generated code patterns
2. **Extend AI Prompts**: Update system prompt in `llm/main.py` for different output formats
3. **Add New Generators**: Create new template files and update generation logic

## 🔍 Key Components Deep Dive

### 1. Natural Language Processor (`src/llm/dsl_generate.py`)
```python
def natural_language_to_yaml(description: str, primary_model: str = None) -> GenerationResult:
    # Converts natural language to structured YAML
    # Uses LLMClient with multi-provider fallback
    # Returns GenerationResult with content and statistics
```

### 2. LLM Provider Wrapper (`src/llm/wrapper/llm_client.py`)
```python
class LLMClient:
    # Manages multiple LLM providers with automatic fallback
    # Tries providers in order: Groq -> OpenRouter -> Gemini -> Ollama
    # Returns GenerationResult with provider info and token stats
```

### 3. State Machine Repair (`src/shared/utils.py`)
```python
def clean_llm_response(content: str) -> str:
    # Removes markdown code blocks from LLM output
    # Handles ```yaml, ```json, and generic ``` blocks

def try_parse_json(content: str) -> dict:
    # Fixes common LLM JSON errors:
    # - Unescaped newlines/quotes in strings
    # - Missing closing braces
    # - Control character issues
```

### 4. Graph-based Relation Validator (`src/dsl/core/modules/relation.py`)
```python
def handle_relations(modules_data: List[Dict], env: Environment, base_output_dir: Path) -> Dict:
    # Creates relation graph with (Entity1, Entity2) tuples as keys
    # Validates all referenced entities exist in module list
    # Detects bidirectional relations by checking reverse edges
    # Automatically infers inverseField for TypeORM decorators
```

### 5. Code Generator (`src/dsl/generate.py`)
```python
def main(blueprint_file: str, nest_project_path: Optional[str] = None) -> None:
    # Orchestrates the entire generation process
    # Loads YAML, processes templates, generates files
    # Handles relations between entities
```

### 6. Module Generator (`src/dsl/core/modules/module.py`)
```python
def generate_module(module_data: Dict, env: Environment, base_output_dir: Path) -> None:
    # Generates individual entity modules
    # Creates DTOs, entities, services, controllers
    # Handles file organization and imports
```

## 🎨 Generated Code Patterns

### Entity Example
```typescript
@Entity('users')
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ unique: true })
  email: string;

  @Column({ length: 50 })
  name: string;

  @OneToMany(() => Post, post => post.user)
  posts: Post[];

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
```

### Controller Example
```typescript
@Controller('users')
@ApiTags('users')
export class UserController {
  @Get()
  @ApiOperation({ summary: 'Get all users' })
  findAll(): Promise<User[]> {
    return this.userService.findAll();
  }

  @Post()
  @ApiOperation({ summary: 'Create user' })
  create(@Body() createUserDto: CreateUserDto): Promise<User> {
    return this.userService.create(createUserDto);
  }
}
```

## 🚀 Capabilities & Features

### Current Features
- ✅ Natural language to YAML conversion
- ✅ Entity relationship modeling (OneToMany, ManyToOne, OneToOne, ManyToMany)
- ✅ Field validation rules
- ✅ CRUD API generation
- ✅ Swagger/OpenAPI documentation
- ✅ TypeORM integration
- ✅ SQLite database support
- ✅ DTO generation with validation
- ✅ Modular NestJS architecture

### Planned Features
- 🔄 Authentication & authorization modules
- 🔄 Database migrations
- 🔄 Testing suite generation
- 🔄 Docker containerization
- 🔄 Multiple database support (PostgreSQL, MySQL)

## 🔧 Technical Dependencies

### Python Dependencies
```
langchain==0.3.27
langchain-google-genai==3.2.0
jinja2
pyyaml
python-dotenv
```

### Generated App Dependencies
```
@nestjs/common
@nestjs/core
@nestjs/typeorm
@nestjs/swagger
typeorm
class-validator
class-transformer
sqlite3
```

## 🎯 Use Cases

### For AI Agents
1. **Rapid Prototyping**: Generate MVPs from feature descriptions
2. **API Design**: Create consistent REST API structures
3. **Database Modeling**: Translate business requirements to data models

### For Development Teams
1. **Boilerplate Generation**: Eliminate repetitive setup tasks
2. **Code Consistency**: Ensure uniform patterns across projects
3. **Learning Tool**: Study generated code to understand NestJS patterns
4. **Template Customization**: Adapt templates for company standards

## ⚠️ Important Notes for Agents

1. **Environment Setup**: Requires at least one LLM provider API key:
   - `GROQ_API_KEY` (recommended - fastest)
   - `OPENROUTER_API_KEY` (alternative)
   - `GOOGLE_API_KEY` (alternative)
   - Or Ollama installed locally
2. **File Paths**: Always use relative paths starting with project root directories
3. **Generated Code**: The `nest_project/src/` directory is auto-generated - don't manually edit
4. **Blueprint Persistence**: Generated blueprints are saved to `blueprint.yaml` by default
5. **Error Handling**: Check logs for template rendering errors or API failures
6. **Provider Fallback**: If primary provider fails, system automatically tries next available provider

This documentation serves as a comprehensive guide for AI agents working with the NestJS code generation system. The project demonstrates the power of combining AI language understanding with structured code generation templates to automate software development workflows.
