#!/usr/bin/env python3
"""
Initialize the nest_project with all necessary dependencies for DSL-generated code.

This script:
1. Creates a new NestJS project if one doesn't exist (using nest CLI)
2. Updates package.json with required packages
3. Installs all npm dependencies

It ensures the nest_project has all dependencies needed for:
- TypeORM (database ORM)
- NestJS modules (TypeORM, Swagger)
- Validation (class-validator, class-transformer)
- Swagger/OpenAPI documentation
"""

import json
import subprocess
import sys
from pathlib import Path


def get_nest_project_path():
    """Get the nest_project path."""
    script_dir = Path(__file__).parent
    nest_project = script_dir / "nest_project"
    return nest_project


def create_nest_project(nest_project_path):
    """Create a new NestJS project using nest CLI."""
    print(f"Creating new NestJS project at {nest_project_path}...")

    try:
        # Check if nest CLI is installed
        result = subprocess.run(
            ["npm", "list", "-g", "@nestjs/cli"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print("Installing @nestjs/cli globally...")
            result = subprocess.run(
                ["npm", "install", "-g", "@nestjs/cli"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print("Error: Failed to install @nestjs/cli globally")
                print(result.stderr)
                return False

        # Create new NestJS project
        parent_dir = nest_project_path.parent
        project_name = nest_project_path.name

        result = subprocess.run(
            ["nest", "new", project_name, "--package-manager", "npm", "--skip-git"],
            cwd=str(parent_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print("Error: Failed to create NestJS project")
            print(result.stderr)
            return False

        print(f"✓ NestJS project created successfully at {nest_project_path}")
        return True
    except subprocess.TimeoutExpired:
        print("Error: nest new command timed out")
        return False
    except FileNotFoundError:
        print("Error: nest CLI not found. Please ensure @nestjs/cli is installed globally")
        print("Install it with: npm install -g @nestjs/cli")
        return False
    except Exception as e:
        print(f"Error creating NestJS project: {e}")
        return False


def update_package_json(nest_project_path):
    """Update package.json with required dependencies."""
    package_json_path = nest_project_path / "package.json"

    if not package_json_path.exists():
        print(f"Error: package.json not found at {package_json_path}")
        return False

    with open(package_json_path, "r") as f:
        package_json = json.load(f)

    # Required dependencies for DSL-generated code
    required_dependencies = {
        "@nestjs/typeorm": "^11.0.0",
        "typeorm": "^0.3.20",
        "@nestjs/swagger": "^8.0.0",
        "@nestjs/mapped-types": "^2.0.5",
        "class-validator": "^0.14.0",
        "class-transformer": "^0.5.1",
        "sqlite3": "^5.1.7",
    }

    # Update dependencies
    if "dependencies" not in package_json:
        package_json["dependencies"] = {}

    added_count = 0
    for package, version in required_dependencies.items():
        if package not in package_json["dependencies"]:
            package_json["dependencies"][package] = version
            print(f"  + Added {package}: {version}")
            added_count += 1
        else:
            print(f"  = {package} already present")

    # Write back to file
    with open(package_json_path, "w") as f:
        json.dump(package_json, f, indent=2)

    if added_count > 0:
        print(f"✓ Updated package.json with {added_count} new dependencies")
    else:
        print("✓ All required dependencies already present in package.json")
    return True


def install_dependencies(nest_project_path):
    """Install npm dependencies."""
    print(f"\nInstalling npm dependencies in {nest_project_path}...")

    try:
        result = subprocess.run(
            ["npm", "install", "--legacy-peer-deps"],
            cwd=str(nest_project_path),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print("Error installing dependencies:")
            print(result.stderr)
            return False

        print("✓ Dependencies installed successfully")
        return True
    except subprocess.TimeoutExpired:
        print("Error: npm install timed out")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def verify_project(nest_project_path):
    """Verify the NestJS project structure."""
    required_files = [
        "package.json",
        "tsconfig.json",
        "src/main.ts",
        "src/app.module.ts",
    ]

    for file in required_files:
        file_path = nest_project_path / file
        if not file_path.exists():
            print(f"Error: Required file missing: {file}")
            return False

    return True


def main():
    """Main execution."""
    print("=" * 70)
    print("NestJS Project Initialization for DSL Code Generation")
    print("=" * 70)

    nest_project_path = get_nest_project_path()

    # Step 0: Create project if it doesn't exist
    if not nest_project_path.exists():
        print("\n0. Creating new NestJS project...")
        if not create_nest_project(nest_project_path):
            print("\n✗ Failed to create NestJS project")
            sys.exit(1)
    else:
        print(f"\n✓ NestJS project already exists at {nest_project_path}")

    # Verify project structure
    if not verify_project(nest_project_path):
        print("\n✗ Project structure verification failed")
        sys.exit(1)

    print(f"Project path: {nest_project_path}")

    # Step 1: Update package.json
    print("\n1. Updating package.json with required dependencies...")
    if not update_package_json(nest_project_path):
        sys.exit(1)

    # Step 2: Install dependencies
    print("\n2. Installing npm dependencies...")
    if not install_dependencies(nest_project_path):
        print("\n✗ npm install failed")
        print("You can try running 'npm install --legacy-peer-deps' manually in nest_project/")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("✓ Initialization complete!")
    print("=" * 70)
    print("\nYou can now run:")
    print("  python test_single_case.py TEST_CASE_1 dsl")
    print("\nOr generate code directly:")
    print("  python dsl/generate.py blueprint.yaml nest_project")
    print("\nTo run the generated application:")
    print("  cd nest_project && npm run start:dev")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
