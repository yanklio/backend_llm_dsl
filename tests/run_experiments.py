
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dsl.generate import main as dsl_generate
from src.llm.raw_generate import natural_language_to_code, save_files
from src.llm.dsl_generate import natural_language_to_yaml
from src.validators import validate_runtime, validate_syntactic
from src.llm.wrapper import GenerationResult

# Suppress stdout/stderr for quieter execution
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open("/dev/null", "w")
        sys.stderr = open("/dev/null", "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

def load_test_cases() -> Dict[str, Any]:
    test_cases_path = Path(__file__).parent / "test_cases.yaml"
    with open(test_cases_path, "r") as f:
        return yaml.safe_load(f)

def clean_project(project_path: Path):
    """Clean src but keep node_modules if possible"""
    src_path = project_path / "src"
    if src_path.exists():
        subprocess.run(["rm", "-rf", str(src_path)], check=True)
    
    # Also clean other files that might be generated in root
    for file in project_path.glob("*.ts"):
        file.unlink()
    for file in project_path.glob("*.json"):
        if file.name not in ["package-lock.json", "package.json", "tsconfig.json", "node_modules"]:
            print(f"Deleting {file.name}")
            file.unlink()
        else:
            print(f"Skipping {file.name}")

def save_results(results: List[Dict[str, Any]]):
    output_file = Path(__file__).parent / "test_results.json"
    try:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"Failed to save results: {e}")

def run_dsl_approach(test_case_name: str, test_case_data: Dict[str, Any], project_path: Path) -> Dict[str, Any]:
    start_time = time.time()
    metrics = {
        "llm_time": 0.0,
        "dsl_time": 0.0,
        "total_time": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "provider": None
    }
    
    blueprint_path = Path(__file__).parent / "test_cases" / "dsl_llm" / f"{test_case_name}_blueprint.yaml"
    blueprint_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # We always regenerate for experiments to capture metrics
        with SuppressOutput():
            # Pass model=None to use default or env var
            result: GenerationResult = natural_language_to_yaml(test_case_data["requirement"])
            
        metrics["llm_time"] = result.duration_seconds
        metrics["input_tokens"] = result.input_tokens
        metrics["output_tokens"] = result.output_tokens
        metrics["total_tokens"] = result.total_tokens
        metrics["provider"] = result.provider
        
        with open(blueprint_path, "w") as f:
            f.write(result.content)
            
        dsl_start = time.time()
        with SuppressOutput():
            dsl_generate(str(blueprint_path), str(project_path))
        metrics["dsl_time"] = time.time() - dsl_start
        
        metrics["total_time"] = time.time() - start_time
        return {"success": True, "metrics": metrics}
        
    except Exception as e:
        metrics["total_time"] = time.time() - start_time
        return {"success": False, "error": str(e), "metrics": metrics}

def run_raw_approach(test_case_name: str, test_case_data: Dict[str, Any], project_path: Path) -> Dict[str, Any]:
    start_time = time.time()
    metrics = {
        "llm_time": 0.0,
        "dsl_time": 0.0, # Not applicable, but kept for schema consistency
        "total_time": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "provider": None
    }
    
    try:
        with SuppressOutput():
            # Pass model=None to use default or env var
            result: GenerationResult = natural_language_to_code(test_case_data["requirement"], str(project_path))
            files = json.loads(result.content)
            save_files(files, str(project_path))
            
        metrics["llm_time"] = result.duration_seconds
        metrics["input_tokens"] = result.input_tokens
        metrics["output_tokens"] = result.output_tokens
        metrics["total_tokens"] = result.total_tokens
        metrics["provider"] = result.provider
        
        metrics["total_time"] = time.time() - start_time
        return {"success": True, "metrics": metrics}
        
    except Exception as e:
        metrics["total_time"] = time.time() - start_time
        return {"success": False, "error": str(e), "metrics": metrics}

def validate_project(project_path: Path) -> Dict[str, Any]:
    with SuppressOutput():
        syntactic = validate_syntactic(str(project_path))
        try:
            # Catch potential validation crashes
            runtime = validate_runtime(str(project_path))
        except Exception as e:
            runtime = {
                "valid": False,
                "install_success": False,
                "build_success": False,
                "start_success": False,
                "error": str(e)
            }
        
    return {
        "syntactic": syntactic,
        "runtime": runtime,
        "overall_valid": syntactic.get("valid", False) and runtime.get("valid", False)
    }

def main():
    test_cases = load_test_cases()
    project_root = Path(__file__).parent.parent
    nest_project_path = project_root / "nest_project"
    
    # Ensure nest_project exists
    nest_project_path.mkdir(exist_ok=True)
    
    results = []
    
    print(f"Starting experiments for {len(test_cases)} test cases...")
    print(f"{'Test Case':<15} {'Approach':<10} {'Status':<10} {'Time':<8} {'Tokens':<8}")
    print("-" * 60)
    
    for case_name, case_data in test_cases.items():
        for approach in ["dsl", "raw"]:
            clean_project(nest_project_path)
            
            if approach == "dsl":
                gen_result = run_dsl_approach(case_name, case_data, nest_project_path)
            else:
                gen_result = run_raw_approach(case_name, case_data, nest_project_path)
            
            validation = {}
            if gen_result["success"]:
                validation = validate_project(nest_project_path)
                status = "PASS" if validation["overall_valid"] else "FAIL"
            else:
                status = "ERR"
                
            metrics = gen_result["metrics"]
            total_tokens = metrics["total_tokens"]
            total_time = metrics["total_time"]
            
            print(f"{case_name:<15} {approach:<10} {status:<10} {total_time:.2f}s   {str(total_tokens):<8}")
            if status == "ERR":
                print(f"  Error: {gen_result.get('error', 'Unknown')}")
            
            current_result = {
                "test_case": case_name,
                "approach": approach,
                "generation": gen_result,
                "validation": validation,
                "timestamp": datetime.now().isoformat()
            }
            results.append(current_result)
            
            # Incremental save
            save_results(results)
            
    print("-" * 60)
    print(f"Results saved to {Path(__file__).parent / 'test_results.json'}")

if __name__ == "__main__":
    main()
