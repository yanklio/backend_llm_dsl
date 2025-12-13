import argparse
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)


def read_project_context(project_dir: str) -> str:
    """Read existing project files for context"""
    project_path = Path(project_dir)

    if not project_path.exists():
        return "No existing project found."

    context = "=== EXISTING PROJECT FILES ===\n\n"

    # Read key files for context
    for file_path in project_path.rglob("*.ts"):
        if "node_modules" not in str(file_path):
            try:
                rel_path = file_path.relative_to(project_path)
                content = file_path.read_text()
                context += f"\n--- {rel_path} ---\n{content}\n"
            except:
                pass

    return context


def natural_language_to_code(description: str, project_dir: str = "./nest_project") -> dict:
    """Generate code from simple description - vibe coder style"""

    existing_context = read_project_context(project_dir)

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
   - typescript, @types/node (devDependencies)

2. **Update DTOs - DO NOT use PartialType**:
   - NEVER import from @nestjs/mapped-types
   - Create simple classes with @IsOptional() on ALL fields
   - Example:
   ```typescript
   export class UpdateUserDto {
     @IsOptional()
     @IsString()
     username?: string;
   }
   ```

3. **TypeORM Config (app.module.ts)**:
   - Use 'sqlite' as database type
   - database: 'database.sqlite'
   - synchronize: true
   - autoLoadEntities: true

4. **Entities MUST have**:
   - @Entity() decorator
   - @PrimaryGeneratedColumn() id field
   - Proper @Column() decorators
   - Relations with cascade options if needed

5. **Services MUST have**:
   - Full CRUD: create, findAll, findOne, update, remove
   - Proper error handling
   - @Injectable() decorator

6. **Controllers MUST have**:
   - @Controller() with route prefix
   - @Get(), @Post(), @Patch(), @Delete() decorators
   - Proper @Body(), @Param() decorators

7. **File Structure**:
   ```
   package.json
   tsconfig.json
   src/main.ts
   src/app.module.ts
   src/app.controller.ts (optional)
   src/app.service.ts (optional)
   src/{entity}/{entity}.entity.ts
   src/{entity}/{entity}.service.ts
   src/{entity}/{entity}.controller.ts
   src/{entity}/{entity}.module.ts
   src/{entity}/dto/create-{entity}.dto.ts
   src/{entity}/dto/update-{entity}.dto.ts
   ```

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

    print("🤖 Asking AI to generate code...")
    response = llm.invoke(messages)

    # Parse JSON response
    content = response.content.strip()

    # Strip markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    content = content.strip()

    import json

    files = json.loads(content)

    return files


def save_files(files: dict, output_dir: str):
    """Save generated files to directory"""
    import json

    output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for file_path, content in files.items():
        try:
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=2)

            full_path.write_text(content, encoding="utf-8")
            print(f"✅ {file_path}")
            saved_count += 1
        except Exception as e:
            print(f"❌ Failed to save {file_path}: {e}")

    print(f"\n📁 Saved {saved_count}/{len(files)} files to: {output_path.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description="Vibe coder - generate NestJS code from simple descriptions"
    )

    parser.add_argument(
        "description", help="What you want (e.g., 'add a Post entity with title and content')"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./nest_project",
        help="Output directory (default: ./nest_project)",
    )

    args = parser.parse_args()

    print("🚀 Vibe Coder - NestJS Generator\n")
    print(f"Request: {args.description}\n")

    try:
        # Generate files
        files = natural_language_to_code(args.description, args.output)

        print(f"\n📝 Generated {len(files)} files\n")

        # Save them
        save_files(files, args.output)

        print("\n🎉 Done! Run with:")
        print(f"  cd {args.output}")
        print("  npm install")
        print("  npm run start:dev")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
