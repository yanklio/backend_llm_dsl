"""Syntactic validation for NestJS projects - Main entry point."""

import json
import sys

from .syntactic_validators import validate_project


def main():
    """Main CLI entry point for syntactic validation."""
    if len(sys.argv) < 2:
        print("Usage: python syntactic.py <project_path>")
        sys.exit(1)

    project_path = sys.argv[1]

    # Run validation
    result = validate_project(project_path)

    # Output results as JSON
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
