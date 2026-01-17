import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dsl.generate import main as dsl_generate
from src.llm.raw_generator import generate_nestjs_backend
from src.llm.yaml_generator import natural_language_to_yaml
from src.validators import validate_runtime, validate_syntactic


def load_test_cases() -> Dict[str, Any]:
    """Load test cases from YAML file."""
    test_cases_path = Path(__file__).parent / "test_cases.yaml"
    with open(test_cases_path, "r") as f:
        return yaml.safe_load(f)


def generate_dsl_approach(test_case_name: str, test_case_data: Dict[str, Any]) -> bool:
    """Generate using DSL approach (YAML -> Code)."""
    print(f"\n{'=' * 60}")
    print("GENERATING WITH DSL APPROACH")
    print(f"{'=' * 60}\n")

    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent
    nest_project_path = project_root / "nest_project"
    blueprint_path = (
        tests_dir / "test_cases" / "dsl_llm" / f"{test_case_name}_blueprint.yaml"
    )

    if not blueprint_path.exists():
        print(f"Error: Blueprint not found at {blueprint_path}")
        print("Generating blueprint from requirement using LLM...")

        try:
            yaml_output = natural_language_to_yaml(test_case_data["requirement"])
            blueprint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(blueprint_path, "w") as f:
                f.write(yaml_output)
            print("✓ Blueprint generated successfully")
        except Exception as e:
            print(f"Failed to generate blueprint: {e}")
            return False

    print(f"Generating code from blueprint: {blueprint_path}")
    try:
        dsl_generate(str(blueprint_path), str(nest_project_path))
        print("✓ Code generation completed")
        return True
    except Exception as e:
        print(f"Generation failed: {e}")
        return False


def generate_raw_approach(test_case_name: str, test_case_data: Dict[str, Any]) -> bool:
    """Generate using RAW LLM approach (Direct code generation)."""
    print(f"\n{'=' * 60}")
    print("GENERATING WITH RAW LLM APPROACH")
    print(f"{'=' * 60}\n")

    project_root = Path(__file__).parent.parent
    nest_project_path = project_root / "nest_project"

    print("Generating code directly from LLM...")
    try:
        generate_nestjs_backend(test_case_data["requirement"], str(nest_project_path))
        print("✓ Direct code generation completed")
        return True
    except Exception as e:
        print(f"Generation failed: {e}")
        return False


def main():
    """Main execution function."""
    if len(sys.argv) < 3:
        print("Usage: python test_single_case.py <test_case_name> <approach>")
        print("\nArguments:")
        print(
            "  test_case_name: TEST_CASE_1, TEST_CASE_2, TEST_CASE_3, TEST_CASE_4, TEST_CASE_5"
        )
        print("  approach: dsl or raw")
        print("\nExample:")
        print("  python test_single_case.py TEST_CASE_1 dsl")
        sys.exit(1)

    test_case_name = sys.argv[1]
    approach = sys.argv[2].lower()

    if approach not in ["dsl", "raw"]:
        print(f"Error: Invalid approach '{approach}'. Use 'dsl' or 'raw'")
        sys.exit(1)

    test_cases = load_test_cases()

    if test_case_name not in test_cases:
        print(f"Error: Test case '{test_case_name}' not found")
        print("\nAvailable test cases:")
        for case_name, case_data in test_cases.items():
            print(f"  - {case_name}: {case_data['name']}")
        sys.exit(1)

    test_case = test_cases[test_case_name]
    endpoints = test_case.get("endpoints", [])

    print("\n" + "=" * 60)
    print(f"TEST CASE: {test_case['name']}")
    print(f"APPROACH: {approach.upper()}")
    print("=" * 60)
    print("\nRequirement:")
    print(test_case["requirement"])
    print(f"\nEndpoints to validate: {len(endpoints)}")
    for ep in endpoints:
        print(f"  - {ep}")

    project_root = Path(__file__).parent.parent
    src_path = project_root / "nest_project" / "src"
    if src_path.exists():
        print(f"\nCleaning {src_path}...")
        subprocess.run(["rm", "-rf", str(src_path)], check=True)

    if approach == "dsl":
        success = generate_dsl_approach(test_case_name, test_case)
    else:
        success = generate_raw_approach(test_case_name, test_case)

    if not success:
        print("\n✗ Generation failed")
        sys.exit(1)

    # 1. Syntactic Validation
    print("\n1 Running Syntactic Validation...")
    nest_project_path = project_root / "nest_project"
    syntactic_result = validate_syntactic(str(nest_project_path))

    print("\nSyntactic Result:")
    print(f"  Valid: {syntactic_result['valid']}")
    print(f"  Error Count: {syntactic_result['error_count']}")

    if syntactic_result["errors"]:
        print(f"\n  Syntax Errors ({len(syntactic_result['errors'])}):")
        for error in syntactic_result["errors"][:5]:  # Show first 5
            print(f"    [{error['file']}:{error['line']}] {error['message'][:80]}")
        if len(syntactic_result["errors"]) > 5:
            print(f"    ... and {len(syntactic_result['errors']) - 5} more errors")

    print("\n2 Running Runtime Validation with Endpoint Testing...")
    runtime_result = validate_runtime(str(nest_project_path))

    print("\nRuntime Result:")
    print(f"  Valid: {runtime_result['valid']}")
    print(f"  Install Success: {runtime_result['install_success']}")
    print(f"  Build Success: {runtime_result['build_success']}")
    print(f"  Start Success: {runtime_result['start_success']}")

    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    overall_valid = syntactic_result["valid"] and runtime_result["valid"]

    print(f"Test Case: {test_case['name']}")
    print(f"Approach: {approach.upper()}")
    print(
        f"Syntactic Validation: {'✓ PASS' if syntactic_result['valid'] else '✗ FAIL'}"
    )
    print(f"Runtime Validation: {'✓ PASS' if runtime_result['valid'] else '✗ FAIL'}")
    print(f"Overall: {'✓ PASS' if overall_valid else '✗ FAIL'}")
    print("=" * 60 + "\n")

    results = {
        "test_case": test_case_name,
        "approach": approach,
        "syntactic": syntactic_result,
        "runtime": [],
        "overall_valid": overall_valid,
    }

    sys.exit(0 if overall_valid else 1)


if __name__ == "__main__":
    main()
