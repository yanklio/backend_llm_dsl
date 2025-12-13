"""
Runtime validation for generated NestJS applications.
Tests if the app builds and runs successfully.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List


def validate_project(project_path: str) -> Dict:
    """
    Validate runtime correctness of a NestJS project.
    
    Args:
        project_path: Path to NestJS project directory
        
    Returns:
        Dictionary with validation results containing:
        - valid: bool
        - build_success: bool
        - start_success: bool
        - errors: List[Dict] with stage and message
    """
    project_path = Path(project_path)
    errors = []
    
    # Check if package.json exists
    if not (project_path / "package.json").exists():
        return {
            "valid": False,
            "build_success": False,
            "start_success": False,
            "errors": [{"stage": "setup", "message": "package.json not found", "code": "MISSING_PACKAGE_JSON"}]
        }
    
    # Install dependencies
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
    build_result = _run_npm_build(project_path)
    if not build_result["success"]:
        errors.append(build_result["error"])
        return {
            "valid": False,
            "build_success": False,
            "start_success": False,
            "errors": errors
        }
    
    # Start the application (quick test)
    start_result = _run_npm_start(project_path)
    if not start_result["success"]:
        errors.append(start_result["error"])
        return {
            "valid": False,
            "build_success": True,
            "start_success": False,
            "errors": errors
        }
    
    return {
        "valid": True,
        "build_success": True,
        "start_success": True,
        "errors": []
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
        # Start the application in background
        process = subprocess.Popen(
            ["npm", "run", "start"],
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a few seconds for app to start
        time.sleep(5)
        
        # Check if process is still running
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
        
        # Terminate the process
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


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python runtime.py <project_path>")
        sys.exit(1)
    
    result = validate_project(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
