
import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.shared import logger
from src.llm.wrapper import LLMClient, GenerationResult

load_dotenv()

def read_project_context(project_dir: str) -> str:
    """Read existing project files for context."""
    project_path = Path(project_dir)

    if not project_path.exists():
        return "No existing project found."

    context = "=== EXISTING PROJECT FILES ===\n\n"

    for file_path in project_path.rglob("*.ts"):
        if "node_modules" not in str(file_path):
            try:
                rel_path = file_path.relative_to(project_path)
                content = file_path.read_text()
                context += f"\n--- {rel_path} ---\n{content}\n"
            except Exception:
                pass

    return context


def natural_language_to_code(
    description: str, project_dir: str = "./nest_project", primary_model: str = None
) -> GenerationResult:
    """Generate code from simple description - vibe coder style."""

    existing_context = read_project_context(project_dir)
    client = LLMClient(temperature=0.2)

    system_prompt = """You are an expert NestJS developer. Generate COMPLETE, WORKING, ERROR-FREE code.

🚨 CRITICAL REQUIREMENTS:

1. **package.json MUST include ALL these dependencies**:
   - @nestjs/common, @nestjs/core, @nestjs/platform-express
   - @nestjs/typeorm, typeorm
   - @nestjs/mapped-types (REQUIRED for Update DTOs)
   - class-validator, class-transformer
   - reflect-metadata, rxjs
   - sqlite3 (for database)
   - @nestjs/cli (devDependencies)

2. **EVERY file must have FULL implementation**:
   - No placeholder comments like "// TODO: implement"
   - No "..." or ellipsis
   - All imports must be correct
   - All decorators must be present

3. **Database setup MUST work**:
   - Use TypeORM with SQLite
   - database.config.ts must export DataSource
   - All entities must have proper decorators

4. **Generate DTOs for all entities**:
   - CreateXxxDTO for POST requests
   - UpdateXxxDTO for PATCH requests
   - Use class-validator decorators

5. **Controllers must have all CRUD endpoints**:
   - GET / (list all)
   - GET /:id (get one)
   - POST / (create)
   - PATCH /:id (update)
   - DELETE /:id (delete)

6. **Services must implement business logic**:
   - Use repository pattern
   - Proper error handling
   - No async/await mistakes

7. **Modules must import everything needed**:
   - TypeOrmModule.forFeature([Entity])
   - All services and controllers exported

Return ONLY valid JSON with NO markdown, NO explanations:
{
  "package.json": {...},
  "tsconfig.json": {...},
  "src/main.ts": "full code",
  "src/app.module.ts": "full code",
  ...
}

MUST compile without errors. MUST run with npm run start:dev. NO PLACEHOLDERS."""

    user_prompt = f"""{existing_context}

=== REQUEST ===
{description}

Generate ALL files needed for a COMPLETE, WORKING NestJS application.
Include package.json, tsconfig.json, and all source files.
Every file must have FULL implementation - no placeholders or TODOs.
Make it production-ready and runnable."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    logger.start("Generating code with LLM...")
    
    result = client.generate(messages, primary_provider_id=primary_model)

    try:
        files = json.loads(result.content)
        logger.success(f"Generated {len(files)} files via {result.provider}")
        return result
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON")
        logger.debug(result.content)
        raise ValueError("Invalid JSON response from LLM")


def save_files(files: Dict[str, Any], output_dir: str) -> None:
    """Save generated files to directory."""
    output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    logger.start(f"Saving files to {output_dir}...")

    saved_count = 0
    for file_path, content in files.items():
        try:
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=2)

            full_path.write_text(content, encoding="utf-8")
            logger.success(f"Saved {file_path}")
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {e}")

    logger.end(f"Saved {saved_count}/{len(files)} files")


def main() -> None:
    """Main execution entry point."""
    parser = argparse.ArgumentParser(
        description="Vibe coder - generate NestJS code from simple descriptions"
    )

    parser.add_argument(
        "description",
        help="What you want (e.g., 'add a Post entity with title and content')",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./nest_project",
        help="Output directory (default: ./nest_project)",
    )
    
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Primary model/provider to use (groq, gemini, openrouter, ollama)",
    )

    args = parser.parse_args()
    
    if args.model:
        logger.info(f"Preferred Model: {args.model}")

    try:
        result = natural_language_to_code(args.description, args.output, args.model)
        
        # Log statistics
        logger.info("=== Generation Statistics ===")
        logger.info(f"Provider: {result.provider}")
        logger.info(f"Time: {result.duration_seconds:.2f}s")
        if result.total_tokens:
            logger.info(f"Tokens: {result.total_tokens} (In: {result.input_tokens}, Out: {result.output_tokens})")

        files = json.loads(result.content)
        save_files(files, args.output)

        logger.success("Done! Run with:")
        logger.info(f"  cd {args.output}")
        logger.info("  npm install")
        logger.info("  npm run start:dev")

    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
