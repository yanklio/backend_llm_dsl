import yaml
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "dsl"))

from dsl.generate import main as dsl_generate_main
from llm.yaml_generator import natural_language_to_yaml, save_blueprint
from llm.raw_generator import natural_language_to_code, save_files


def load_test_cases(file_path: str = 'test_cases.yaml') -> dict:
    """Load test cases from YAML file"""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def generate_dsl_llm(case_id: str, requirement: str) -> bool:
    """Generate backend using DSL_LLM approach (LLM -> YAML -> Templates)"""
    blueprint_path = f"./test_cases/dsl_llm/{case_id}_blueprint.yaml"
    project_path = f"./test_cases/dsl_llm/{case_id}_backend"
    
    print(f"🤖 [DSL_LLM] Generating blueprint with LLM...")
    print(f"📄 Blueprint: {blueprint_path}")
    print(f"📁 Project: {project_path}")
    
    try:
        # Generate blueprint from natural language
        blueprint = natural_language_to_yaml(requirement)
        save_blueprint(blueprint, blueprint_path)
        print("✅ Blueprint generated!")
        print()
        
        # Generate backend code from blueprint
        print("🔧 Generating backend code...")
        dsl_generate_main(blueprint_path, project_path)
        print("✅ [DSL_LLM] Backend code generated!")
        return True
        
    except Exception as e:
        print(f"❌ [DSL_LLM] Failed to process {case_id}: {e}")
        return False


def generate_raw_llm(case_id: str, requirement: str) -> bool:
    """Generate backend using RAW_LLM approach (LLM -> Direct Code)"""
    project_path = f"./test_cases/raw_llm/{case_id}_backend"
    
    print(f"🤖 [RAW_LLM] Generating code directly with LLM...")
    print(f"📁 Project: {project_path}")
    
    try:
        # Generate complete backend code directly from natural language
        files = natural_language_to_code(requirement, project_path)
        
        print(f"\n📝 Generated {len(files)} files\n")
        
        # Save all generated files
        save_files(files, project_path)
        
        print("✅ [RAW_LLM] Backend code generated!")
        return True
        
    except Exception as e:
        print(f"❌ [RAW_LLM] Failed to process {case_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_test_case(case_id: str, case_data: dict) -> dict:
    """Process a single test case with both approaches"""
    print(f"\n{'='*80}")
    print(f"Processing: {case_id}")
    print(f"{'='*80}")
    print(f"Name: {case_data['name']}")
    print(f"\nRequirement:")
    print(case_data['requirement'])
    print()
    
    results = {
        'case_id': case_id,
        'name': case_data['name'],
        'dsl_llm_success': False,
        'raw_llm_success': False
    }
    
    # Generate using DSL_LLM approach
    results['dsl_llm_success'] = generate_dsl_llm(case_id, case_data['requirement'])
    print()
    
    # Generate using RAW_LLM approach
    results['raw_llm_success'] = generate_raw_llm(case_id, case_data['requirement'])
    
    print(f"{'='*80}\n")
    
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
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for result in all_results:
        dsl_status = "✅" if result['dsl_llm_success'] else "❌"
        raw_status = "✅" if result['raw_llm_success'] else "❌"
        print(f"{result['case_id']}: DSL_LLM {dsl_status} | RAW_LLM {raw_status}")
    print("="*80)


if __name__ == "__main__":
    main()

