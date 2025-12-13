#!/usr/bin/env python3
"""
Validation script for comparing DSL-template vs. raw-LLM code generation.
Runs syntactic validation on test case outputs.
"""

import json
from pathlib import Path
from typing import Dict, List
from validate.syntactic import validate_project


def validate_test_cases(base_path: Path, skip_compilation: bool = False) -> Dict[str, Dict]:
    """
    Validate all test case backends in a directory.
    
    Args:
        base_path: Path to test_cases/dsl_llm or test_cases/raw_llm
        skip_compilation: If True, skip TypeScript compilation
        
    Returns:  
        Dictionary mapping test case name to validation results
    """
    results = {}
    
    # Find all backend directories (TEST_CASE_*_backend)
    for backend_dir in sorted(base_path.glob("TEST_CASE_*_backend")):
        test_case_name = backend_dir.name
        
        print(f"Validating {test_case_name}...")
        
        result = validate_project(str(backend_dir), skip_compilation=skip_compilation)
        results[test_case_name] = result
        
        if result["valid"]:
            print(f"  ✓ Valid ({result['total_files']} files)")
        else:
            print(f"  ✗ Invalid ({result['error_count']} errors in {result['total_files']} files)")
            for error in result["errors"][:3]:  # Show first 3 errors
                print(f"     - {error['code']}: {error['message']}")
    
    return results


def compare_approaches():
    """
    Compare syntactic validation results between DSL and raw LLM approaches.
    """
    base_dir = Path(__file__).parent
    dsl_path = base_dir / "test_cases" / "dsl_llm"
    raw_path = base_dir / "test_cases" / "raw_llm"
    
    print("=" * 60)
    print("SYNTACTIC VALIDATION COMPARISON")
    print("=" * 60)
    
    # Validate DSL approach (skip compilation - no tsconfig)
    print("\n🔧 DSL-Template Approach (structure only):")
    print("-" * 60)
    dsl_results = validate_test_cases(dsl_path, skip_compilation=True)
    
    # Validate raw LLM approach (with compilation)
    print("\n🤖 Raw-LLM Approach (with TypeScript compilation):")
    print("-" * 60)
    raw_results = validate_test_cases(raw_path, skip_compilation=False)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    dsl_valid = sum(1 for r in dsl_results.values() if r["valid"])
    dsl_total = len(dsl_results)
    dsl_errors = sum(r["error_count"] for r in dsl_results.values())
    
    raw_valid = sum(1 for r in raw_results.values() if r["valid"])
    raw_total = len(raw_results)
    raw_errors = sum(r["error_count"] for r in raw_results.values())
    
    print(f"\nDSL-Template: {dsl_valid}/{dsl_total} test cases valid ({dsl_errors} total errors)")
    print(f"Raw-LLM:      {raw_valid}/{raw_total} test cases valid ({raw_errors} total errors)")
    
    # Save detailed results
    output_file = base_dir / "validation_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "dsl_template": dsl_results,
            "raw_llm": raw_results,
            "summary": {
                "dsl": {
                    "valid_count": dsl_valid,
                    "total_count": dsl_total,
                    "error_count": dsl_errors,
                    "success_rate": dsl_valid / dsl_total if dsl_total > 0 else 0
                },
                "raw": {
                    "valid_count": raw_valid,
                    "total_count": raw_total,
                    "error_count": raw_errors,
                    "success_rate": raw_valid / raw_total if raw_total > 0 else 0
                }
            }
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return dsl_results, raw_results


if __name__ == "__main__":
    compare_approaches()
