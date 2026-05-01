"""Export experiment results to CSV files."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import ANALYTICS_DIR, RUNS_DIR

APPROACH_ORDER = ["dsl", "raw", "mixed"]
TIER_ORDER = ["simple", "medium", "complex"]
STATUS_ORDER = ["PASS", "FAIL", "ERR"]


def _load_json(path: Path) -> Any:
    """Load JSON content from a path."""
    with open(path) as file_handle:
        return json.load(file_handle)


def _run_dirs(runs_dir: Path, selected_run_ids: list[str] | None = None) -> list[Path]:
    """Return experiment run directories to include in analytics."""
    if selected_run_ids:
        return [runs_dir / run_id for run_id in selected_run_ids]
    return sorted(path for path in runs_dir.iterdir() if path.is_dir() and (path / "results.json").exists())


def _assign_repetition_indexes(run_metadata: list[dict[str, Any]]) -> dict[str, int]:
    """Assign repetition numbers per approach based on chronological run order."""
    by_approach: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metadata in run_metadata:
        approach = metadata["approaches"][0] if len(metadata.get("approaches", [])) == 1 else "all"
        by_approach[approach].append(metadata)

    repetition_indexes = {}
    for approach_metadata in by_approach.values():
        for index, metadata in enumerate(sorted(approach_metadata, key=lambda item: item["created_at"]), start=1):
            repetition_indexes[metadata["run_id"]] = index
    return repetition_indexes


def load_records(runs_dir: Path, selected_run_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Load and flatten records from experiment run folders."""
    run_dirs = _run_dirs(runs_dir, selected_run_ids)
    metadata_by_run = {}
    for run_dir in run_dirs:
        metadata = _load_json(run_dir / "metadata.json")
        metadata_by_run[metadata["run_id"]] = metadata
    repetition_indexes = _assign_repetition_indexes(list(metadata_by_run.values()))

    records = []
    for run_dir in run_dirs:
        metadata = _load_json(run_dir / "metadata.json")
        for record in _load_json(run_dir / "results.json"):
            records.append(_flatten_record(record, metadata, repetition_indexes[metadata["run_id"]]))
    return records


def _flatten_record(record: dict[str, Any], metadata: dict[str, Any], repetition: int) -> dict[str, Any]:
    """Flatten nested result data into a CSV-friendly row."""
    generation = record.get("generation", {})
    metrics = generation.get("metrics", {})
    validation = record.get("validation", {})
    syntactic = validation.get("syntactic", {})
    runtime = validation.get("runtime", {})
    status = _status_for(record)
    first_error = _first_error(validation)

    return {
        "repetition": repetition,
        "run_id": record.get("run_id", metadata.get("run_id", "")),
        "run_created_at": metadata.get("created_at", ""),
        "provider": record.get("provider", ""),
        "model_name": record.get("model_name", ""),
        "approach": record.get("approach", ""),
        "test_case": record.get("test_case", ""),
        "tier": record.get("tier", ""),
        "prompt_version": record.get("prompt_version", ""),
        "prompt_hash": record.get("prompt_hash", ""),
        "timestamp": record.get("timestamp", ""),
        "status": status,
        "generation_success": generation.get("success", False),
        "overall_valid": validation.get("overall_valid", False),
        "syntactic_valid": syntactic.get("valid", False),
        "runtime_valid": runtime.get("valid", False),
        "install_success": runtime.get("install_success", False),
        "build_success": runtime.get("build_success", False),
        "start_success": runtime.get("start_success", False),
        "error_count": syntactic.get("error_count", 0),
        "total_files": syntactic.get("total_files", 0),
        "total_time": metrics.get("total_time", 0),
        "llm_time": metrics.get("llm_time", 0),
        "dsl_time": metrics.get("dsl_time", 0),
        "input_tokens": metrics.get("input_tokens", 0),
        "output_tokens": metrics.get("output_tokens", 0),
        "total_tokens": metrics.get("total_tokens", 0),
        "phase1_input_tokens": metrics.get("phase1_input_tokens", 0),
        "phase1_output_tokens": metrics.get("phase1_output_tokens", 0),
        "phase1_total_tokens": metrics.get("phase1_total_tokens", 0),
        "phase2_input_tokens": metrics.get("phase2_input_tokens", 0),
        "phase2_output_tokens": metrics.get("phase2_output_tokens", 0),
        "phase2_total_tokens": metrics.get("phase2_total_tokens", 0),
        "first_error_file": first_error.get("file", ""),
        "first_error_code": first_error.get("code", ""),
        "first_error_message": first_error.get("message", ""),
    }


def _status_for(record: dict[str, Any]) -> str:
    """Return PASS, FAIL, or ERR for one result record."""
    generation = record.get("generation", {})
    validation = record.get("validation", {})
    if not generation.get("success", False):
        return "ERR"
    if validation.get("overall_valid", False):
        return "PASS"
    return "FAIL"


def _first_error(validation: dict[str, Any]) -> dict[str, Any]:
    """Return the first available validation error for qualitative CSV output."""
    syntactic_errors = validation.get("syntactic", {}).get("errors", [])
    if syntactic_errors:
        return syntactic_errors[0]

    runtime_errors = validation.get("runtime", {}).get("errors", {})
    for stage, error in runtime_errors.items():
        if error:
            return {"file": stage, "code": error.get("code", ""), "message": error.get("message", "")}
    return {}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dictionaries to CSV, creating an empty file if no rows exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def _group_rows(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Aggregate records by the given keys."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[tuple(record[key] for key in keys)].append(record)

    rows = []
    for group_values, group_records in sorted(grouped.items(), key=lambda item: item[0]):
        total = len(group_records)
        passed = sum(1 for record in group_records if record["status"] == "PASS")
        failed = sum(1 for record in group_records if record["status"] == "FAIL")
        errors = sum(1 for record in group_records if record["status"] == "ERR")
        row = dict(zip(keys, group_values))
        row.update(
            {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "success_rate": round(passed / total, 4) if total else 0,
                "avg_total_time": round(_mean(record["total_time"] for record in group_records), 4),
                "avg_llm_time": round(_mean(record["llm_time"] for record in group_records), 4),
                "avg_input_tokens": round(_mean(record["input_tokens"] for record in group_records), 2),
                "avg_output_tokens": round(_mean(record["output_tokens"] for record in group_records), 2),
                "avg_total_tokens": round(_mean(record["total_tokens"] for record in group_records), 2),
            }
        )
        rows.append(row)
    return rows


def _mean(values: Any) -> float:
    """Compute mean for an iterable of numeric values."""
    value_list = [float(value or 0) for value in values]
    return sum(value_list) / len(value_list) if value_list else 0.0


def export_csvs(records: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    """Export normalized records and summaries to CSV files."""
    csv_dir = output_dir / "csv"
    failure_rows = [record for record in records if record["status"] != "PASS"]
    files = {
        "records": csv_dir / "records.csv",
        "summary_by_approach": csv_dir / "summary_by_approach.csv",
        "summary_by_approach_tier": csv_dir / "summary_by_approach_tier.csv",
        "summary_by_repetition_approach": csv_dir / "summary_by_repetition_approach.csv",
        "failures": csv_dir / "failures.csv",
    }

    _write_csv(files["records"], records)
    _write_csv(files["summary_by_approach"], _group_rows(records, ("approach",)))
    _write_csv(files["summary_by_approach_tier"], _group_rows(records, ("approach", "tier")))
    _write_csv(files["summary_by_repetition_approach"], _group_rows(records, ("repetition", "approach")))
    _write_csv(files["failures"], failure_rows)
    return files


def _ordered_approach_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort approach summary rows in the thesis display order."""
    return sorted(rows, key=lambda row: APPROACH_ORDER.index(row["approach"]))


def _ordered_approach_tier_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort approach/tier rows in the thesis display order."""
    return sorted(rows, key=lambda row: (APPROACH_ORDER.index(row["approach"]), TIER_ORDER.index(row["tier"])))


def _default_output_dir() -> Path:
    """Build the timestamped analytics output path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return ANALYTICS_DIR / timestamp


def export_analytics(runs_dir: Path, output_dir: Path, selected_run_ids: list[str] | None = None) -> None:
    """Export CSV artifacts from experiment run directories."""
    records = load_records(runs_dir, selected_run_ids)
    if not records:
        raise ValueError(f"No experiment records found in {runs_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_files = export_csvs(records, output_dir)

    print(f"Exported {len(records)} records to {output_dir}")
    for label, path in csv_files.items():
        print(f"- {label}: {path}")


def main() -> None:
    """Parse CLI arguments and export analytics artifacts."""
    parser = argparse.ArgumentParser(description="Export experiment analytics as CSV files.")
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR, help="Directory containing experiment run folders")
    parser.add_argument("--output", type=Path, default=None, help="Output analytics directory")
    parser.add_argument("--run-id", action="append", dest="run_ids", help="Specific run ID to include; repeatable")
    args = parser.parse_args()

    export_analytics(
        runs_dir=args.runs_dir,
        output_dir=args.output or _default_output_dir(),
        selected_run_ids=args.run_ids,
    )


if __name__ == "__main__":
    main()
