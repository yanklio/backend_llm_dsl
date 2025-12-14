"""Endpoint testing utilities for runtime validation."""

import socket
import time
from pathlib import Path
from typing import Dict, List

import requests

from ..shared.error_types import ErrorCodes, create_error
from ..shared.subprocess_utils import check_process_running, start_process, terminate_process


def is_port_in_use(port: int, host: str = "localhost") -> bool:
    """
    Check if a port is currently in use.

    Args:
        port: Port number to check
        host: Host to check on

    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def test_endpoints(
    project_path: Path, endpoints: List[str], base_url: str = "http://localhost:3000"
) -> Dict:
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
        # Check if port is already in use
        port = 3000
        if is_port_in_use(port):
            return {
                "success": False,
                "results": {},
                "errors": [
                    create_error(
                        "endpoint_test",
                        f"Port {port} is already in use. Please free the port before testing.",
                        ErrorCodes.START_ERROR,
                    )
                ],
            }

        # Start the application
        process = start_process(["npm", "run", "start"], cwd=project_path)
        time.sleep(8)

        is_running, error_output = check_process_running(process)

        if not is_running:
            error_message = error_output[:200] if error_output else "Application crashed"
            return {
                "success": False,
                "results": {},
                "errors": [
                    create_error(
                        "endpoint_test",
                        f"Application crashed before testing: {error_message}",
                        ErrorCodes.APP_CRASHED,
                    )
                ],
            }

        # Test each endpoint
        for endpoint in endpoints:
            endpoint_result = test_single_endpoint(endpoint, base_url)
            results[endpoint] = endpoint_result

            if not endpoint_result["success"]:
                errors.append(
                    create_error(
                        "endpoint_test",
                        f"Endpoint {endpoint} failed: {endpoint_result.get('error', 'Unknown error')}",
                        ErrorCodes.ENDPOINT_FAILED,
                        endpoint=endpoint,
                    )
                )

        return {"success": len(errors) == 0, "results": results, "errors": errors}

    except Exception as e:
        return {
            "success": False,
            "results": results,
            "errors": [
                create_error(
                    "endpoint_test",
                    f"Endpoint testing error: {str(e)}",
                    ErrorCodes.ENDPOINT_TEST_ERROR,
                )
            ],
        }
    finally:
        # Clean up process - ensure it's terminated even if exception occurs
        if process:
            try:
                terminate_process(process)
            except Exception as cleanup_error:
                # Log cleanup error but don't override main error
                if not errors:
                    errors.append(
                        create_error(
                            "cleanup",
                            f"Failed to cleanup process: {str(cleanup_error)}",
                            ErrorCodes.START_ERROR,
                        )
                    )


def test_single_endpoint(endpoint: str, base_url: str) -> Dict:
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
                "status_code": None,
            }

        method, path = parts
        method = method.upper()

        url = f"{base_url}{path}"

        # Prepare test data for POST/PUT requests
        test_data = {}
        if method in ["POST", "PUT"]:
            test_data = {"test": "data"}

        # Execute HTTP request
        response = _execute_http_request(method, url, test_data)

        if response is None:
            return {
                "success": False,
                "error": f"Unsupported HTTP method: {method}",
                "status_code": None,
            }

        success = response.status_code < 300

        return {
            "success": success,
            "status_code": response.status_code,
            "error": None if success else f"Server error: {response.status_code}",
            "response_time_ms": int(response.elapsed.total_seconds() * 1000),
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Connection refused - endpoint not available",
            "status_code": None,
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout", "status_code": None}
    except Exception as e:
        return {"success": False, "error": f"Request error: {str(e)}", "status_code": None}


def _execute_http_request(method: str, url: str, data: Dict, timeout: int = 10):
    """
    Execute HTTP request based on method.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        url: Full URL to request
        data: Request body data
        timeout: Request timeout in seconds

    Returns:
        Response object or None if method unsupported
    """
    if method == "GET":
        return requests.get(url, timeout=timeout)
    elif method == "POST":
        return requests.post(url, json=data, timeout=timeout)
    elif method == "PUT":
        return requests.put(url, json=data, timeout=timeout)
    elif method == "DELETE":
        return requests.delete(url, timeout=timeout)
    else:
        return None
