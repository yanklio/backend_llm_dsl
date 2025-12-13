#!/usr/bin/env python3
"""
Test script to validate NestJS applications with endpoint testing.
Uses test cases from test_cases.yaml
"""

import sys
import yaml
from validate.runtime import validate_project


def main():
    """Run runtime validation with endpoint testing for all test cases."""
    
    # Load test cases
    with open('test_cases.yaml', 'r') as f:
        test_cases = yaml.safe_load(f)
    
    if len(sys.argv) < 2:
        print("Usage: python test_runtime_endpoints.py <test_case_name> <project_path>")
        print("\nAvailable test cases:")
        for case_name in test_cases.keys():
            print(f"  - {case_name}: {test_cases[case_name]['name']}")
        sys.exit(1)
    
    test_case_name = sys.argv[1]
    project_path = sys.argv[2] if len(sys.argv) > 2 else f"./test_cases/dsl_llm/{test_case_name}_backend"
    
    if test_case_name not in test_cases:
        print(f"Error: Test case '{test_case_name}' not found")
        print("\nAvailable test cases:")
        for case_name in test_cases.keys():
            print(f"  - {case_name}")
        sys.exit(1)
    
    # Get test case data
    test_case = test_cases[test_case_name]
    endpoints = test_case.get('endpoints', [])
    
    print(f"\n{'='*60}")
    print(f"Running validation for: {test_case['name']}")
    print(f"Project path: {project_path}")
    print(f"Endpoints to test: {len(endpoints)}")
    print(f"{'='*60}\n")
    
    # Run validation
    result = validate_project(project_path, endpoints)
    
    # Print results
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    print(f"Overall Valid: {result['valid']}")
    print(f"Build Success: {result['build_success']}")
    print(f"Start Success: {result['start_success']}")
    
    if result.get('endpoint_tests'):
        print(f"\nEndpoint Tests:")
        for endpoint, test_result in result['endpoint_tests'].items():
            status = "✓" if test_result['success'] else "✗"
            status_code = test_result.get('status_code', 'N/A')
            response_time = test_result.get('response_time_ms', 'N/A')
            print(f"  {status} {endpoint:30} [{status_code}] {response_time}ms")
            if not test_result['success']:
                print(f"      Error: {test_result.get('error', 'Unknown')}")
    
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"  [{error['stage']}] {error['message']}")
    
    print("="*60 + "\n")
    
    sys.exit(0 if result['valid'] else 1)


if __name__ == "__main__":
    main()
