import subprocess
import sys
from pathlib import Path

import yaml

from llm.raw_generator import generate_nestjs_backend
from llm.yaml_generator import natural_language_to_yaml
from validators import validate_runtime, validate_syntactic

# Add dsl directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "dsl"))
from generate import main as dsl_generate


def load_test_cases():
    """Load test cases from YAML file."""
    with open("test_cases.yaml", "r") as f:
        return yaml.safe_load(f)


def generate_dsl_approach(test_case_name, test_case_data):
    """Generate using DSL approach (YAML -> Code)."""
    print(f"\n{'=' * 60}")
    print("GENERATING WITH DSL APPROACH")
    print(f"{'=' * 60}\n")

    blueprint_path = f"test_cases/dsl_llm/{test_case_name}_blueprint.yaml"

    if not Path(blueprint_path).exists():
        print(f"Error: Blueprint not found at {blueprint_path}")
        print("Generating blueprint from requirement using LLM...")

        try:
            yaml_output = natural_language_to_yaml(test_case_data["requirement"])
            with open(blueprint_path, "w") as f:
                f.write(yaml_output)
            print("✓ Blueprint generated successfully")
        except Exception as e:
            print(f"Failed to generate blueprint: {e}")
            return False

    print(f"Generating code from blueprint: {blueprint_path}")
    try:
        dsl_generate(blueprint_path, "nest_project")
        print("✓ Code generation completed")
        return True
    except Exception as e:
        print(f"Generation failed: {e}")
        return False


def generate_raw_approach(test_case_name, test_case_data):
    """Generate using RAW LLM approach (Direct code generation)."""
    print(f"\n{'=' * 60}")
    print("GENERATING WITH RAW LLM APPROACH")
    print(f"{'=' * 60}\n")

    print("Generating code directly from LLM...")
    try:
        generate_nestjs_backend(test_case_data["requirement"], "nest_project")
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
        print("  test_case_name: TEST_CASE_1, TEST_CASE_2, TEST_CASE_3, TEST_CASE_4, TEST_CASE_5")
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

    src_path = Path("nest_project/src")
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
    syntactic_result = validate_syntactic("nest_project")

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
    runtime_result = validate_runtime("nest_project")

    print("\nRuntime Result:")
    print(f"  Valid: {runtime_result['valid']}")
    print(f"  Install Success: {runtime_result['install_success']}")
    print(f"  Build Success: {runtime_result['build_success']}")
    print(f"  Start Success: {runtime_result['start_success']}")

    # if runtime_result["errors"]:
    #     print("  Errors:")
    #     for error in runtime_result["errors"]:
    #         print(f"    {error}")

    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    overall_valid = syntactic_result["valid"] and runtime_result["valid"]

    print(f"Test Case: {test_case['name']}")
    print(f"Approach: {approach.upper()}")
    print(f"Syntactic Validation: {'✓ PASS' if syntactic_result['valid'] else '✗ FAIL'}")
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

    # output_file = f"nest_project/validation_result_{approach}.json"
    # with open(output_file, "w") as f:
    #     json.dump(results, f, indent=2)
    # print(f"Results saved to: {output_file}")

    sys.exit(0 if overall_valid else 1)


if __name__ == "__main__":
    main()
