"""Runtime validation for NestJS projects - Main entry point."""

import json
import sys
from typing import List, Optional

import yaml
from runtime_validators import validate_project


def load_endpoints_from_yaml(test_case_name: str, test_cases_file: str) -> Optional[List[str]]:
    """
    Load endpoints from a YAML test cases file.

    Args:
        test_case_name: Name of the test case to load
        test_cases_file: Path to the YAML test cases file

    Returns:
        List of endpoints or None if not found
    """
    try:
        with open(test_cases_file, "r") as f:
            test_cases = yaml.safe_load(f)
            if test_case_name in test_cases:
                return test_cases[test_case_name].get("endpoints", [])
    except Exception as e:
        print(f"Warning: Could not load test cases: {e}", file=sys.stderr)

    return None


def main():
    """Main CLI entry point for runtime validation."""
    if len(sys.argv) < 2:
        print("Usage: python runtime.py <project_path> [test_case_name] [test_cases_yaml]")
        sys.exit(1)

    project_path = sys.argv[1]
    endpoints = None

    # Load endpoints from test cases if provided
    if len(sys.argv) >= 4:
        test_case_name = sys.argv[2]
        test_cases_file = sys.argv[3]
        endpoints = load_endpoints_from_yaml(test_case_name, test_cases_file)

    # Run validation
    result = validate_project(project_path, endpoints)

    # Output results as JSON
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
