"""
Syntactic correctness validation for generated TypeScript code.
Uses TypeScript Compiler (tsc --noEmit) to check for syntax errors.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List


def validate_project(project_path: str) -> Dict:
    """
    Validate syntactic correctness of a NestJS project using tsc --noEmit.
    
    Args:
        project_path: Path to NestJS project directory
        
    Returns:
        Dictionary with validation results containing:
        - valid: bool
        - total_files: int
        - error_count: int
        - errors: List[Dict] with file, line, column, message, code
    """
    project_path = Path(project_path)
    src_path = project_path / "src"
    
    if not src_path.exists():
        return {
            "valid": False,
            "total_files": 0,
            "error_count": 1,
            "errors": [{"file": "", "line": 0, "column": 0, "message": f"Source directory not found: {src_path}", "code": "MISSING_SRC"}]
        }
    
    ts_files = list(src_path.rglob("*.ts"))
    total_files = len(ts_files)
    
    if total_files == 0:
        return {
            "valid": False,
            "total_files": 0,
            "error_count": 1,
            "errors": [{"file": "", "line": 0, "column": 0, "message": "No TypeScript files found", "code": "NO_FILES"}]
        }
    
    if not (project_path / "tsconfig.json").exists():
        return {
            "valid": False,
            "total_files": total_files,
            "error_count": 1,
            "errors": [{"file": "", "line": 0, "column": 0, "message": "tsconfig.json not found", "code": "MISSING_CONFIG"}]
        }
    
    errors = _run_tsc(project_path)
    
    return {
        "valid": len(errors) == 0,
        "total_files": total_files,
        "error_count": len(errors),
        "errors": errors
    }


def _run_tsc(project_path: Path) -> List[Dict]:
    """Execute TypeScript compiler and parse errors."""
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        errors = []
        output = result.stdout + result.stderr
        
        for line in output.splitlines():
            error = _parse_error_line(line)
            if error:
                errors.append(error)
        
        return errors
        
    except subprocess.TimeoutExpired:
        return [{"file": "", "line": 0, "column": 0, "message": "TypeScript compilation timeout", "code": "TIMEOUT"}]
    except FileNotFoundError:
        return [{"file": "", "line": 0, "column": 0, "message": "TypeScript compiler not found (npx tsc)", "code": "TSC_NOT_FOUND"}]
    except Exception as e:
        return [{"file": "", "line": 0, "column": 0, "message": f"Validation error: {str(e)}", "code": "ERROR"}]


def _parse_error_line(line: str) -> Dict | None:
    """
    Parse TypeScript compiler error line.
    
    Format: src/user/user.entity.ts(12,5): error TS2322: Type 'string' is not assignable to type 'number'.
    """
    if "error TS" not in line:
        return None
    
    try:
        parts = line.split("): error ")
        if len(parts) != 2:
            return None
        
        file_loc = parts[0].split("(")
        if len(file_loc) != 2:
            return None
        
        file_path = file_loc[0].strip()
        line_col = file_loc[1].strip()
        
        line_num, col_num = 0, 0
        if "," in line_col:
            coords = line_col.split(",")
            line_num = int(coords[0])
            col_num = int(coords[1])
        
        error_part = parts[1]
        code = ""
        message = error_part
        
        if error_part.startswith("TS"):
            code_end = error_part.find(":")
            if code_end > 0:
                code = error_part[:code_end].strip()
                message = error_part[code_end + 1:].strip()
        
        return {
            "file": file_path,
            "line": line_num,
            "column": col_num,
            "message": message,
            "code": code
        }
        
    except Exception:
        return {"file": "", "line": 0, "column": 0, "message": line, "code": "PARSE_ERROR"}



if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python syntactic.py <project_path>")
        sys.exit(1)
    
    result = validate_project(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)
