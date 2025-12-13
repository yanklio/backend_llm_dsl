#!/usr/bin/env python3
"""
Complete validation script for NestJS projects.
Runs both syntactic and runtime validation.
"""

import json
import sys
from pathlib import Path
from validate.syntactic import validate_project as validate_syntactic
from validate.runtime import validate_project as validate_runtime


def main():
    project_path = Path(__file__).parent / "nest_project"
    
    print("=" * 60)
    print("COMPLETE VALIDATION - nest_project")
    print("=" * 60)
    print(f"\nProject path: {project_path}\n")
    
    # Syntactic Validation
    print("🔍 SYNTACTIC VALIDATION")
    print("-" * 60)
    syntactic_result = validate_syntactic(str(project_path))
    
    print(f"Status: {'✓ VALID' if syntactic_result['valid'] else '✗ INVALID'}")
    print(f"Total files: {syntactic_result['total_files']}")
    print(f"Error count: {syntactic_result['error_count']}")
    
    if syntactic_result['errors']:
        print(f"\nErrors found:")
        for i, error in enumerate(syntactic_result['errors'][:3], 1):
            print(f"  {i}. [{error['code']}] {error['file']}")
            if error['line'] > 0:
                print(f"     Line {error['line']}, Column {error['column']}")
            print(f"     {error['message']}")
    
    # Runtime Validation
    print(f"\n🚀 RUNTIME VALIDATION")
    print("-" * 60)
    print("Running validation (this may take a few minutes)...")
    
    runtime_result = validate_runtime(str(project_path))
    
    print(f"Status: {'✓ VALID' if runtime_result['valid'] else '✗ INVALID'}")
    print(f"Build success: {'✓' if runtime_result['build_success'] else '✗'}")
    print(f"Start success: {'✓' if runtime_result['start_success'] else '✗'}")
    
    if runtime_result['errors']:
        print(f"\nErrors found:")
        for i, error in enumerate(runtime_result['errors'], 1):
            print(f"  {i}. Stage: {error['stage']}")
            print(f"     [{error['code']}] {error['message']}")
    
    # Overall Summary
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    overall_valid = syntactic_result['valid'] and runtime_result['valid']
    print(f"Overall Status: {'✓ VALID' if overall_valid else '✗ INVALID'}")
    print(f"  Syntactic: {'✓' if syntactic_result['valid'] else '✗'}")
    print(f"  Runtime:   {'✓' if runtime_result['valid'] else '✗'}")
    
    # Save combined results
    output_file = project_path / "validation_result.json"
    combined_result = {
        "valid": overall_valid,
        "syntactic": syntactic_result,
        "runtime": runtime_result
    }
    
    with open(output_file, "w") as f:
        json.dump(combined_result, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    sys.exit(0 if overall_valid else 1)


if __name__ == "__main__":
    main()
