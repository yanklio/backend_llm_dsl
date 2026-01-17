import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "dsl"))

from dsl.generate import main as dsl_generate_main
from llm.raw_generator import natural_language_to_code, save_files
from llm.yaml_generator import natural_language_to_yaml, save_blueprint
from shared import logger


def load_test_cases(file_path: str = "test_cases.yaml") -> dict:
    """Load test cases from YAML file"""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def generate_dsl_llm(case_id: str, requirement: str) -> bool:
    """Generate backend using DSL_LLM approach (LLM -> YAML -> Templates)"""
    blueprint_path = f"./test_cases/dsl_llm/{case_id}_blueprint.yaml"
    project_path = f"./test_cases/dsl_llm/{case_id}_backend"

    logger.start(f"[DSL_LLM] Generating {case_id}")

    try:
        # Generate blueprint from natural language
        logger.info("Generating blueprint with LLM...")
        blueprint = natural_language_to_yaml(requirement)
        save_blueprint(blueprint, blueprint_path)
        logger.success("Blueprint generated")

        # Generate backend code from blueprint
        logger.info("Generating backend code...")
        dsl_generate_main(blueprint_path, project_path)
        logger.success("[DSL_LLM] Backend code generated")
        return True

    except Exception as e:
        logger.error(f"[DSL_LLM] Failed to process {case_id}: {e}")
        return False


def generate_raw_llm(case_id: str, requirement: str) -> bool:
    """Generate backend using RAW_LLM approach (LLM -> Direct Code)"""
    project_path = f"./test_cases/raw_llm/{case_id}_backend"

    logger.start(f"[RAW_LLM] Generating {case_id}")

    try:
        # Generate complete backend code directly from natural language
        logger.info("Generating code directly with LLM...")
        files = natural_language_to_code(requirement, project_path)
        logger.success(f"Generated {len(files)} files")

        # Save all generated files
        save_files(files, project_path)

        logger.success("[RAW_LLM] Backend code generated")
        return True

    except Exception as e:
        logger.error(f"[RAW_LLM] Failed to process {case_id}: {e}")
        import traceback

        traceback.print_exc()
        return False


def process_test_case(case_id: str, case_data: dict) -> dict:
    """Process a single test case with both approaches"""
    logger.start(f"Processing {case_id}: {case_data['name']}")
    logger.info(f"Requirement: {case_data['requirement'][:60]}...")

    results = {
        "case_id": case_id,
        "name": case_data["name"],
        "dsl_llm_success": False,
        "raw_llm_success": False,
    }

    # Generate using DSL_LLM approach
    results["dsl_llm_success"] = generate_dsl_llm(case_id, case_data["requirement"])

    # Generate using RAW_LLM approach
    results["raw_llm_success"] = generate_raw_llm(case_id, case_data["requirement"])

    logger.end(f"Completed {case_id}")

    return results


def main():
    """Main execution function"""
    test_cases = load_test_cases()

    all_results = []

    # Process each test case
    for case_id, case_data in test_cases.items():
        result = process_test_case(case_id, case_data)
        all_results.append(result)

    # Print summary
    logger.start("SUMMARY")
    for result in all_results:
        dsl_status = "✓" if result["dsl_llm_success"] else "✗"
        raw_status = "✓" if result["raw_llm_success"] else "✗"
        logger.info(f"{result['case_id']}: DSL_LLM {dsl_status} | RAW_LLM {raw_status}")
    logger.end("All cases processed")


if __name__ == "__main__":
    main()
