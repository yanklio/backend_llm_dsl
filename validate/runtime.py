"""
Runtime validation for generated NestJS applications.
Tests if the app builds and runs successfully.
"""

import json
import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional


def validate_project(project_path: str, endpoints: Optional[List[str]] = None, base_url: str = "http://localhost:3000") -> Dict:
    """
    Validate runtime correctness of a NestJS project.
    
    Args:
        project_path: Path to NestJS project directory
        endpoints: Optional list of endpoints to test (e.g., ["GET /users", "POST /users"])
        base_url: Base URL of the running application
        
    Returns:
        Dictionary with validation results containing:
        - valid: bool
        - build_success: bool
        - start_success: bool
        - endpoint_tests: Dict with endpoint test results (if endpoints provided)
        - errors: List[Dict] with stage and message
    """
    project_path = Path(project_path)
    errors = []
    
    if not (project_path / "package.json").exists():
        return {
            "valid": False,
            "build_success": False,
            "start_success": False,
            "errors": [{"stage": "setup", "message": "package.json not found", "code": "MISSING_PACKAGE_JSON"}]
        }
    
    install_result = _run_npm_install(project_path)
    if not install_result["success"]:
        errors.append(install_result["error"])
        return {
            "valid": False,
            "build_success": False,
            "start_success": False,
            "errors": errors
        }
    
    # Build the project
    if not build_result["success"]:
        errors.append(build_result["error"])
        return {
            "valid": False,
            "build_success": False,
            "start_success": False,
            "errors": errors
        }
    
    start_result = _run_npm_start(project_path)
    if not start_result["success"]:
        errors.append(start_result["error"])
        return {
            "valid": False,
            "build_success": True,
            "start_success": False,
            "errors": errors
        }
    
    endpoint_results = {}
    if endpoints:
        endpoint_test = _test_endpoints(project_path, endpoints, base_url)
        endpoint_results = endpoint_test["results"]
        if not endpoint_test["success"]:
            errors.extend(endpoint_test["errors"])
    
    return {
        "valid": len(errors) == 0,
        "build_success": True,
        "start_success": True,
        "endpoint_tests": endpoint_results,
        "errors": errors
    }


def _run_npm_install(project_path: Path) -> Dict:
    """Install npm dependencies."""
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": {
                    "stage": "install",
                    "message": f"npm install failed: {result.stderr[:200]}",
                    "code": "INSTALL_FAILED"
                }
            }
        
        return {"success": True}
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": {"stage": "install", "message": "npm install timeout", "code": "INSTALL_TIMEOUT"}
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": {"stage": "install", "message": "npm not found", "code": "NPM_NOT_FOUND"}
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"stage": "install", "message": f"Install error: {str(e)}", "code": "INSTALL_ERROR"}
        }


def _run_npm_build(project_path: Path) -> Dict:
    """Build the NestJS project."""
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": {
                    "stage": "build",
                    "message": f"npm run build failed: {result.stderr[:200]}",
                    "code": "BUILD_FAILED"
                }
            }
        
        return {"success": True}
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": {"stage": "build", "message": "Build timeout", "code": "BUILD_TIMEOUT"}
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"stage": "build", "message": f"Build error: {str(e)}", "code": "BUILD_ERROR"}
        }


def _run_npm_start(project_path: Path) -> Dict:
    """Start the application and verify it runs."""
    try:
        process = subprocess.Popen(
            ["npm", "run", "start"],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(5)
        
        if process.poll() is not None:
            _, stderr = process.communicate()
            return {
                "success": False,
                "error": {
                    "stage": "start",
                    "message": f"Application crashed: {stderr[:200]}",
                    "code": "START_CRASHED"
                }
            }
        
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        
        return {"success": True}
        
    except Exception as e:
        return {
            "success": False,
            "error": {"stage": "start", "message": f"Start error: {str(e)}", "code": "START_ERROR"}
        }


def _test_endpoints(project_path: Path, endpoints: List[str], base_url: str) -> Dict:
    """
    Test the provided endpoints by starting the app and sending HTTP requests.
    
    Args:
        project_path: Path to NestJS project
        endpoints: List of endpoints in format "METHOD /path" (e.g., "GET /users")
        base_url: Base URL of the application
        
    Returns:
        Dictionary with success status, results per endpoint, and errors
    """
    results = {}
    errors = []
    process = None
    
    try:
        # Start the application
        process = subprocess.Popen(
            ["npm", "run", "start"],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        time.sleep(8)
        
        if process.poll() is not None:
            _, stderr = process.communicate()
            return {
                "success": False,
                "results": {},
                "errors": [{
                    "stage": "endpoint_test",
                    "message": f"Application crashed before testing: {stderr[:200]}",
                    "code": "APP_CRASHED"
                }]
            }
        
        # Test each endpoint
        for endpoint in endpoints:
            endpoint_result = _test_single_endpoint(endpoint, base_url)
            results[endpoint] = endpoint_result
            
            if not endpoint_result["success"]:
                errors.append({
                    "stage": "endpoint_test",
                    "message": f"Endpoint {endpoint} failed: {endpoint_result.get('error', 'Unknown error')}",
                    "code": "ENDPOINT_FAILED",
                    "endpoint": endpoint
                })
        
        return {
            "success": len(errors) == 0,
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        return {
            "success": False,
            "results": results,
            "errors": [{
                "stage": "endpoint_test",
                "message": f"Endpoint testing error: {str(e)}",
                "code": "ENDPOINT_TEST_ERROR"
            }]
        }
    finally:
        # Clean up process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def _test_single_endpoint(endpoint: str, base_url: str) -> Dict:
    """
    Test a single endpoint.
    
    Args:
        endpoint: Endpoint in format "METHOD /path"
        base_url: Base URL of the application
        
    Returns:
        Dictionary with success status, status_code, and error message if failed
    """
    try:
        parts = endpoint.strip().split(" ", 1)
        if len(parts) != 2:
            return {
                "success": False,
                "error": f"Invalid endpoint format: {endpoint}",
                "status_code": None
            }
        
        method, path = parts
        method = method.upper()
        
        url = f"{base_url}{path}"
        
        test_data = {}
        if method in ["POST", "PUT"]:
            test_data = {"test": "data"}
        
        response = None
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=test_data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=test_data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {
                "success": False,
                "error": f"Unsupported HTTP method: {method}",
                "status_code": None
            }
        
        # Check response
        # Accept 2xx, 4xx responses (endpoint exists and responds)
        # 5xx indicates server error
        success = response.status_code < 500
        
        return {
            "success": success,
            "status_code": response.status_code,
            "error": None if success else f"Server error: {response.status_code}",
            "response_time_ms": int(response.elapsed.total_seconds() * 1000)
        }
        
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection refused - endpoint not available",
            "status_code": None
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout",
            "status_code": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Request error: {str(e)}",
            "status_code": None
        }


if __name__ == "__main__":
    import sys
    import yaml
    
    if len(sys.argv) < 2:
        print("Usage: python runtime.py <project_path> [test_case_name] [test_cases_yaml]")
        sys.exit(1)
    
    project_path = sys.argv[1]
    endpoints = None
    
    # Load endpoints from test cases if provided
    if len(sys.argv) >= 4:
        test_case_name = sys.argv[2]
        test_cases_file = sys.argv[3]
        
        try:
            with open(test_cases_file, 'r') as f:
                test_cases = yaml.safe_load(f)
                if test_case_name in test_cases:
                    endpoints = test_cases[test_case_name].get('endpoints', [])
        except Exception as e:
            print(f"Warning: Could not load test cases: {e}", file=sys.stderr)
    
    result = validate_project(project_path, endpoints)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
