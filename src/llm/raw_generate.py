
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
from src.shared.utils import clean_llm_response, try_parse_json
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

    system_prompt = """You are an expert NestJS developer. Generate COMPLETE, WORKING, ERROR-FREE code for src/ directory.

🚨 CRITICAL REQUIREMENTS:


1. **EVERY file must have FULL implementation**:
   - No placeholder comments like "// TODO: implement"
   - No "..." or ellipsis
   - All imports must be correct
   - All decorators must be present

2. **Database setup MUST work**:
  - Use TypeORM with SQLite
   - database.config.ts must export DataSource
   - All entities must have proper decorators

3. **Generate DTOs for all entities**:
   - CreateXxxDTO for POST requests
   - UpdateXxxDTO for PATCH requests
   - Use class-validator decorators

4. **Controllers must have all CRUD endpoints**:
   - GET / (list all)
   - GET /:id (get one)
   - POST / (create)
   - PATCH /:id (update)
   - DELETE /:id (delete)

5. **Services must implement business logic**:
   - Use repository pattern
   - Proper error handling
   - No async/await mistakes

6. **Modules must import everything needed**:
   - TypeOrmModule.forFeature([Entity])
   - All services and controllers exported

7. **Only create files outside src/ directory**:
   - Do not create package.json or tsconfig.json
   - Do not create files in node_modules/
   - Do not create files in dist/

For context you will be already given this dependencies list from package.json (do not include it in the generated code):

"dependencies": {
    "@nestjs/common": "^11.0.1",
    "@nestjs/core": "^11.0.1",
    "@nestjs/platform-express": "^11.0.1",
    "reflect-metadata": "^0.2.2",
    "rxjs": "^7.8.1",
    "@nestjs/typeorm": "^11.0.0",
    "typeorm": "^0.3.20",
    "@nestjs/swagger": "^8.0.0",
    "@nestjs/mapped-types": "^2.0.5",
    "class-validator": "^0.14.0",
    "class-transformer": "^0.5.1",
    "sqlite3": "^5.1.7"
  },
  "devDependencies": {
    "@eslint/eslintrc": "^3.2.0",
    "@eslint/js": "^9.18.0",
    "@nestjs/cli": "^11.0.0",
    "@nestjs/schematics": "^11.0.0",
    "@nestjs/testing": "^11.0.1",
    "@types/express": "^5.0.0",
    "@types/jest": "^30.0.0",
    "@types/node": "^22.10.7",
    "@types/supertest": "^6.0.2",
    "eslint": "^9.18.0",
    "eslint-config-prettier": "^10.0.1",
    "eslint-plugin-prettier": "^5.2.2",
    "globals": "^16.0.0",
    "jest": "^30.0.0",
    "prettier": "^3.4.2",
    "source-map-support": "^0.5.21",
    "supertest": "^7.0.0",
    "ts-jest": "^29.2.5",
    "ts-loader": "^9.5.2",
    "ts-node": "^10.9.2",
    "tsconfig-paths": "^4.2.0",
    "typescript": "^5.7.3",
    "typescript-eslint": "^8.20.0"
  },

Return a SINGLE VALID JSON object mapping file paths to file content.
DO NOT output raw code. DO NOT output markdown blocks (unless wrapping the JSON).
DO NOT acknowledge the request. Just output the JSON.

Return a SINGLE VALID JSON object where:
1. Keys are file paths (e.g., "src/main.ts")
2. Values are the FULL FILE CONTENT as properly escaped JSON strings
   - The output MUST be valid JSON parseable by standard JSON parsers
   - Newlines in file content must be represented as the JSON escape sequence \\n (backslash followed by n)
   - Double quotes must be escaped as \\"
   - Backslashes must be escaped as \\\\
   - Do NOT return objects, arrays, or metadata for the files. Just the code string.
   - Do NOT generate .map, .d.ts, or compiled .js files. Only .ts source files.

Example structure (note how newlines are \\n in the JSON):
{
  "src/app.module.ts": "import { Module } from '@nestjs/common';\\n\\n@Module({\\n  imports: [],\\n})\\nexport class AppModule {}"
}

CRITICAL: The output must be pure, valid JSON. NO text before or after. NO markdown code blocks.
Test your output mentally: it should be parseable by json.loads() or JSON.parse()."""

    user_prompt = f"""{existing_context}

=== REQUEST ===
{description}

Generate ALL files needed for a COMPLETE, WORKING NestJS application inside src/ directory.
Every file must have FULL implementation - no placeholders or TODOs.
Make it production-ready and runnable."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    logger.start("Generating code with LLM...")
    
    result = client.generate(messages, primary_provider_id=primary_model)

    try:
        cleaned_content = clean_llm_response(result.content)
        result.content = cleaned_content
        files = try_parse_json(cleaned_content)
        logger.success(f"Generated {len(files)} files via {result.provider}")
        return result
    except Exception as e:
        logger.error("Failed to parse LLM response as JSON")
        logger.error(f"Parse error: {str(e)}")
        
        # Save to file for debugging
        debug_file = Path("/tmp/llm_response_debug.json")
        debug_file.write_text(cleaned_content)
        logger.error(f"Saved malformed response to {debug_file}")
        
        logger.error("First 2000 chars of cleaned response:")
        logger.error(cleaned_content[:2000])
        logger.error("Last 500 chars of cleaned response:")
        logger.error(cleaned_content[-500:])
        raise ValueError(f"Invalid JSON response from LLM: {str(e)}")


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
            
            if isinstance(content, str) and "\\n" in content:
                if content.count("\\n") > content.count("\n") * 2:
                    logger.warn(f"Detected literal escape sequences in {file_path}, fixing...")
                    content = content.replace("\\n", "\n")
                    content = content.replace("\\t", "\t")
                    content = content.replace('\\"', '"')
                    content = content.replace("\\\\", "\\")

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

        cleaned_content = clean_llm_response(result.content)
        files = try_parse_json(cleaned_content)
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
