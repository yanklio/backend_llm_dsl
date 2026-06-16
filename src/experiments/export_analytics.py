"""Export experiment results to CSV files and thesis charts."""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import ANALYTICS_DIR, RUNS_DIR

APPROACH_ORDER = ["dsl", "textual_dsl", "textual-gen", "raw", "mixed"]
TIER_ORDER = ["simple", "medium", "complex"]
STATUS_ORDER = ["PASS", "FAIL", "ERR"]
APPROACH_LABELS = {
    "dsl": "DSL",
    "textual_dsl": "Textual DSL",
    "textual-gen": "Textual Gen",
    "raw": "Raw",
    "mixed": "Mixed",
}
TIER_LABELS = {"simple": "Proste", "medium": "Średnie", "complex": "Złożone"}
STATUS_LABELS = {"PASS": "Poprawne", "FAIL": "Niepoprawne", "ERR": "Błąd generacji"}
STATUS_COLORS = {"PASS": "#4E79A7", "FAIL": "#A0A0A0", "ERR": "#6B6B6B"}
APPROACH_COLORS = {
    "dsl": "#4E79A7",
    "textual_dsl": "#F28E2B",
    "textual-gen": "#E15759",
    "raw": "#7F7F7F",
    "mixed": "#59A14F",
}
ERROR_CATEGORY_ORDER = [
    "generation_error",
    "typescript_syntax",
    "dependency_install",
    "build_validation",
    "runtime_startup",
    "validation_other",
]
ERROR_CATEGORY_LABELS = {
    "generation_error": "Generowanie",
    "typescript_syntax": "TypeScript",
    "dependency_install": "Instalacja zależności",
    "build_validation": "Build",
    "runtime_startup": "Uruchomienie",
    "validation_other": "Inna walidacja",
}
ERROR_CATEGORY_COLORS = {
    "generation_error": "#4E79A7",
    "typescript_syntax": "#7F7F7F",
    "dependency_install": "#A0A0A0",
    "build_validation": "#B8B8B8",
    "runtime_startup": "#59A14F",
    "validation_other": "#6B6B6B",
}
TYPESCRIPT_ERROR_GROUP_ORDER = [
    "nullability_return",
    "nullability_assignment",
    "missing_module_import",
    "missing_symbol_import",
    "dto_property_mismatch",
    "typeorm_query_typing",
    "library_api_mismatch",
    "duplicate_declaration",
    "invalid_function_signature",
    "invalid_computed_property",
    "enum_export_issue",
    "typescript_other",
]
TYPESCRIPT_ERROR_GROUP_LABELS = {
    "nullability_return": "Nullable return type",
    "nullability_assignment": "Nullable assignment",
    "missing_module_import": "Missing module import",
    "missing_symbol_import": "Missing symbol/import",
    "dto_property_mismatch": "DTO/property mismatch",
    "typeorm_query_typing": "TypeORM query typing",
    "library_api_mismatch": "Library API mismatch",
    "duplicate_declaration": "Duplicate declaration",
    "invalid_function_signature": "Invalid function signature",
    "invalid_computed_property": "Invalid computed property",
    "enum_export_issue": "Enum/export issue",
    "typescript_other": "Other TypeScript",
}
TYPESCRIPT_ERROR_GROUP_COLORS = {
    "nullability_return": "#4E79A7",
    "nullability_assignment": "#A0CBE8",
    "missing_module_import": "#7F7F7F",
    "missing_symbol_import": "#B8B8B8",
    "dto_property_mismatch": "#59A14F",
    "typeorm_query_typing": "#8CD17D",
    "library_api_mismatch": "#9C755F",
    "duplicate_declaration": "#BAB0AC",
    "invalid_function_signature": "#F1CE63",
    "invalid_computed_property": "#D4A6C8",
    "enum_export_issue": "#D7B5A6",
    "typescript_other": "#6B6B6B",
}
SYSTEMATIC_MIN_AFFECTED_RECORDS = 3
SYSTEMATIC_MIN_APPROACHES = 2


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
    first_error = _first_error(record)
    error_category = _error_category_for(record)
    typescript_errors = _typescript_error_rows(record)
    alignment = _prompt_alignment_fields(record)

    return {
        "_typescript_errors": typescript_errors,
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
        "error_category": error_category,
        "error_category_label": _error_category_label(error_category),
        **alignment,
    }


def _prompt_alignment_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Return flattened prompt-alignment fields for one record."""
    alignment = record.get("prompt_alignment", {})
    result = alignment.get("result") if isinstance(alignment, dict) else None
    result = result if isinstance(result, dict) else {}
    missing_requirements = result.get("missing_requirements", [])
    extra_features = result.get("extra_features", [])
    metrics = alignment.get("metrics", {}) if isinstance(alignment, dict) else {}
    source_files = alignment.get("source_files", {}) if isinstance(alignment, dict) else {}

    return {
        "alignment_provider": alignment.get("provider", "") if isinstance(alignment, dict) else "",
        "alignment_model_name": alignment.get("model_name", "") if isinstance(alignment, dict) else "",
        "alignment_prompt_version": alignment.get("prompt_version", "") if isinstance(alignment, dict) else "",
        "alignment_prompt_hash": alignment.get("prompt_hash", "") if isinstance(alignment, dict) else "",
        "alignment_score": result.get("alignment_score", ""),
        "alignment_missing_requirements_count": len(missing_requirements)
        if isinstance(missing_requirements, list)
        else 0,
        "alignment_extra_features_count": len(extra_features) if isinstance(extra_features, list) else 0,
        "alignment_rationale": result.get("rationale", ""),
        "alignment_error": alignment.get("error", "") if isinstance(alignment, dict) else "",
        "alignment_duration_seconds": metrics.get("duration_seconds", 0),
        "alignment_input_tokens": metrics.get("input_tokens", 0),
        "alignment_output_tokens": metrics.get("output_tokens", 0),
        "alignment_total_tokens": metrics.get("total_tokens", 0),
        "alignment_source_file_count": source_files.get("count", 0),
        "alignment_source_total_characters": source_files.get("total_characters", 0),
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


def _first_error(record: dict[str, Any]) -> dict[str, Any]:
    """Return the first available generation or validation error."""
    generation = record.get("generation", {})
    if not generation.get("success", False):
        return {
            "file": "generation",
            "code": "GENERATION_ERROR",
            "message": generation.get("error", "Unknown generation error"),
        }

    validation = record.get("validation", {})
    syntactic_errors = validation.get("syntactic", {}).get("errors", [])
    if syntactic_errors:
        return syntactic_errors[0]

    runtime_errors = validation.get("runtime", {}).get("errors", {})
    for stage, error in runtime_errors.items():
        if error:
            return {"file": stage, "code": error.get("code", ""), "message": error.get("message", "")}
    return {}


def _error_category_for(record: dict[str, Any]) -> str:
    """Assign one stable, thesis-friendly error category to a result record."""
    generation = record.get("generation", {})
    if not generation.get("success", False):
        return "generation_error"

    validation = record.get("validation", {})
    if validation.get("overall_valid", False):
        return ""

    syntactic = validation.get("syntactic", {})
    if not syntactic.get("valid", True):
        return "typescript_syntax"

    runtime = validation.get("runtime", {})
    runtime_errors = runtime.get("errors", {})
    if runtime_errors.get("install") or not runtime.get("install_success", True):
        return "dependency_install"
    if runtime_errors.get("build") or not runtime.get("build_success", True):
        return "build_validation"
    if runtime_errors.get("start") or not runtime.get("start_success", True):
        return "runtime_startup"
    return "validation_other"


def _typescript_error_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return classified TypeScript error rows for one experiment record."""
    errors = record.get("validation", {}).get("syntactic", {}).get("errors", [])
    rows = []
    for index, error in enumerate(errors, start=1):
        code = error.get("code", "")
        message = error.get("message", "")
        group = _typescript_error_group_for(code, message)
        rows.append(
            {
                "error_index": index,
                "typescript_error_group": group,
                "typescript_error_group_label": _typescript_error_group_label(group),
                "typescript_error_code": code,
                "typescript_error_file": error.get("file", ""),
                "typescript_error_line": error.get("line", ""),
                "typescript_error_column": error.get("column", ""),
                "typescript_error_message": message,
            }
        )
    return rows


def _typescript_error_group_for(code: str, message: str) -> str:
    """Map TypeScript compiler errors to thesis-level root-cause groups."""
    normalized_message = message.lower()

    if code == "TS2322" and "promise<" in normalized_message and "| null" in normalized_message:
        return "nullability_return"
    if code in {"TS2322", "TS2345"} and "null" in normalized_message and "not assignable" in normalized_message:
        return "nullability_assignment"
    if code == "TS2307" or "cannot find module" in normalized_message:
        return "missing_module_import"
    if code in {"TS2304", "TS2552"} or "cannot find name" in normalized_message:
        return "missing_symbol_import"
    if code == "TS2551" or "does not exist on type" in normalized_message:
        return "dto_property_mismatch"
    if code == "TS2769" or "no overload matches this call" in normalized_message:
        return "typeorm_query_typing"
    if "no exported member" in normalized_message:
        return "library_api_mismatch"
    if code == "TS2300" or "duplicate identifier" in normalized_message:
        return "duplicate_declaration"
    if code == "TS1016" or "required parameter cannot follow an optional parameter" in normalized_message:
        return "invalid_function_signature"
    if code == "TS2464" or "computed property name" in normalized_message:
        return "invalid_computed_property"
    if code == "TS2459" or "declares" in normalized_message and "not exported" in normalized_message:
        return "enum_export_issue"
    return "typescript_other"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write dictionaries to CSV, creating an empty file if no rows exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    public_rows = [_public_row(row) for row in rows]
    fieldnames = list(public_rows[0].keys()) if public_rows else []
    with open(path, "w", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(public_rows)


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    """Remove internal analytics fields before writing public CSV output."""
    return {key: value for key, value in row.items() if not key.startswith("_")}


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
                "alignment_scored_records": _count_present_scores(group_records),
                "avg_alignment_score": round(_mean_present_scores(group_records), 2),
            }
        )
        rows.append(row)
    return rows


def _group_error_category_rows(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Aggregate non-passing records by error category and selected keys."""
    error_records = [record for record in records if record["error_category"]]
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in error_records:
        grouped[tuple(record[key] for key in keys)].append(record)

    rows = []
    for group_values, group_records in sorted(grouped.items(), key=_error_group_sort_key):
        row = dict(zip(keys, group_values))
        row["error_category_label"] = _error_category_label(row["error_category"])
        row["count"] = len(group_records)
        rows.append(row)
    return rows


def _typescript_error_detail_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten every TypeScript compiler error into a dedicated CSV row."""
    rows = []
    base_fields = (
        "repetition",
        "run_id",
        "provider",
        "model_name",
        "approach",
        "test_case",
        "tier",
        "prompt_version",
        "prompt_hash",
    )
    for record in records:
        for error in record.get("_typescript_errors", []):
            row = {field: record[field] for field in base_fields}
            row.update(error)
            rows.append(row)
    return rows


def _group_typescript_error_rows(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Aggregate TypeScript error detail rows by selected dimensions."""
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)

    summary_rows = []
    for group_values, group_rows in sorted(grouped.items(), key=_typescript_error_sort_key):
        row = dict(zip(keys, group_values))
        if "typescript_error_group" in row:
            row["typescript_error_group_label"] = _typescript_error_group_label(row["typescript_error_group"])
        row["count"] = len(group_rows)
        row["affected_records"] = len({(item["run_id"], item["approach"], item["test_case"]) for item in group_rows})
        summary_rows.append(row)
    return summary_rows


def _systematic_typescript_error_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return TypeScript error groups that repeat across records or approaches."""
    grouped_rows = _group_typescript_error_rows(rows, ("typescript_error_group",))
    approaches_by_group: dict[str, set[str]] = defaultdict(set)
    cases_by_group: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        group = row["typescript_error_group"]
        approaches_by_group[group].add(row["approach"])
        cases_by_group[group].add(row["test_case"])

    systematic_rows = []
    for row in grouped_rows:
        group = row["typescript_error_group"]
        approach_count = len(approaches_by_group[group])
        is_systematic = (
            row["affected_records"] >= SYSTEMATIC_MIN_AFFECTED_RECORDS or approach_count >= SYSTEMATIC_MIN_APPROACHES
        )
        if not is_systematic:
            continue

        systematic_rows.append(
            {
                **row,
                "affected_cases": len(cases_by_group[group]),
                "affected_approaches": ",".join(sorted(approaches_by_group[group])),
                "classification": "systematic",
            }
        )
    return sorted(systematic_rows, key=lambda item: (-item["count"], item["typescript_error_group"]))


def _typescript_error_sort_key(item: tuple[tuple[Any, ...], list[dict[str, Any]]]) -> tuple[Any, ...]:
    """Sort TypeScript error summaries in stable display order."""
    group_values = item[0]
    sort_values = []
    for value in group_values:
        if value in APPROACH_ORDER:
            sort_values.append(APPROACH_ORDER.index(value))
        elif value in TYPESCRIPT_ERROR_GROUP_ORDER:
            sort_values.append(TYPESCRIPT_ERROR_GROUP_ORDER.index(value))
        elif value in TIER_ORDER:
            sort_values.append(TIER_ORDER.index(value))
        else:
            sort_values.append(value)
    return tuple(sort_values)


def _error_group_sort_key(item: tuple[tuple[Any, ...], list[dict[str, Any]]]) -> tuple[Any, ...]:
    """Sort error category summaries in approach and category display order."""
    group_values = item[0]
    sort_values = []
    for value in group_values:
        if value in APPROACH_ORDER:
            sort_values.append(APPROACH_ORDER.index(value))
        elif value in ERROR_CATEGORY_ORDER:
            sort_values.append(ERROR_CATEGORY_ORDER.index(value))
        else:
            sort_values.append(value)
    return tuple(sort_values)


def _mean(values: Any) -> float:
    """Compute mean for an iterable of numeric values."""
    value_list = [float(value or 0) for value in values]
    return sum(value_list) / len(value_list) if value_list else 0.0


def _alignment_scores(records: list[dict[str, Any]]) -> list[float]:
    """Return present prompt-alignment scores from flattened records."""
    scores = []
    for record in records:
        score = record.get("alignment_score", "")
        if score == "":
            continue
        scores.append(float(score))
    return scores


def _count_present_scores(records: list[dict[str, Any]]) -> int:
    """Count records with a prompt-alignment score."""
    return len(_alignment_scores(records))


def _mean_present_scores(records: list[dict[str, Any]]) -> float:
    """Compute the mean prompt-alignment score for judged records only."""
    scores = _alignment_scores(records)
    return sum(scores) / len(scores) if scores else 0.0


def export_csvs(records: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    """Export normalized records and summaries to CSV files."""
    csv_dir = output_dir / "csv"
    failure_rows = [record for record in records if record["status"] != "PASS"]
    typescript_error_rows = _typescript_error_detail_rows(records)
    files = {
        "records": csv_dir / "records.csv",
        "summary_by_approach": csv_dir / "summary_by_approach.csv",
        "summary_by_approach_tier": csv_dir / "summary_by_approach_tier.csv",
        "summary_by_repetition_approach": csv_dir / "summary_by_repetition_approach.csv",
        "failures": csv_dir / "failures.csv",
        "error_categories": csv_dir / "error_categories.csv",
        "error_categories_by_approach": csv_dir / "error_categories_by_approach.csv",
        "typescript_errors": csv_dir / "typescript_errors.csv",
        "typescript_error_groups": csv_dir / "typescript_error_groups.csv",
        "typescript_error_groups_by_approach": csv_dir / "typescript_error_groups_by_approach.csv",
        "typescript_error_groups_by_tier": csv_dir / "typescript_error_groups_by_tier.csv",
        "systematic_typescript_error_groups": csv_dir / "systematic_typescript_error_groups.csv",
    }

    _write_csv(files["records"], records)
    _write_csv(files["summary_by_approach"], _group_rows(records, ("approach",)))
    _write_csv(files["summary_by_approach_tier"], _group_rows(records, ("approach", "tier")))
    _write_csv(files["summary_by_repetition_approach"], _group_rows(records, ("repetition", "approach")))
    _write_csv(files["failures"], failure_rows)
    _write_csv(files["error_categories"], _group_error_category_rows(records, ("error_category",)))
    _write_csv(
        files["error_categories_by_approach"],
        _group_error_category_rows(records, ("approach", "error_category")),
    )
    _write_csv(files["typescript_errors"], typescript_error_rows)
    _write_csv(
        files["typescript_error_groups"],
        _group_typescript_error_rows(typescript_error_rows, ("typescript_error_group",)),
    )
    _write_csv(
        files["typescript_error_groups_by_approach"],
        _group_typescript_error_rows(typescript_error_rows, ("approach", "typescript_error_group")),
    )
    _write_csv(
        files["typescript_error_groups_by_tier"],
        _group_typescript_error_rows(typescript_error_rows, ("tier", "typescript_error_group")),
    )
    _write_csv(
        files["systematic_typescript_error_groups"],
        _systematic_typescript_error_rows(typescript_error_rows),
    )
    return files


def export_charts(records: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    """Export readable Polish-labeled PNG charts for thesis figures."""
    plt = _load_matplotlib()
    _configure_matplotlib(plt)

    chart_dir = output_dir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    approach_rows = _ordered_approach_rows(_group_rows(records, ("approach",)))
    approach_tier_rows = _ordered_approach_tier_rows(_group_rows(records, ("approach", "tier")))

    files = {
        "success_by_approach": chart_dir / "success_by_approach.png",
        "success_by_tier": chart_dir / "success_by_tier.png",
        "status_by_approach": chart_dir / "status_by_approach.png",
        "average_costs": chart_dir / "average_costs.png",
        "errors_by_category": chart_dir / "errors_by_category.png",
        "typescript_errors_by_group": chart_dir / "typescript_errors_by_group.png",
        "systematic_typescript_errors": chart_dir / "systematic_typescript_errors.png",
    }

    _plot_success_by_approach(plt, approach_rows, files["success_by_approach"])
    _plot_success_by_tier(plt, approach_tier_rows, files["success_by_tier"])
    _plot_status_by_approach(plt, approach_rows, files["status_by_approach"])
    _plot_average_costs(plt, approach_rows, files["average_costs"])
    _plot_errors_by_category(plt, records, files["errors_by_category"])
    _plot_typescript_errors_by_group(plt, records, files["typescript_errors_by_group"])
    _plot_systematic_typescript_errors(plt, records, files["systematic_typescript_errors"])
    return files


def _load_matplotlib() -> Any:
    """Load matplotlib with a non-interactive backend and a clear dependency error."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as error:
        raise RuntimeError("matplotlib is required for chart export. Run: pip install -r requirements.txt") from error
    return plt


def _configure_matplotlib(plt: Any) -> None:
    """Configure matplotlib defaults for readable thesis figures."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.labelcolor": "#222222",
            "axes.titleweight": "bold",
            "axes.titlesize": 14,
            "axes.labelsize": 11,
            "font.size": 10,
            "legend.frameon": False,
            "xtick.color": "#222222",
            "ytick.color": "#222222",
            "savefig.facecolor": "white",
        }
    )


def _plot_success_by_approach(plt: Any, rows: list[dict[str, Any]], path: Path) -> None:
    """Plot total success rate by approach."""
    fig, ax = plt.subplots(figsize=(8.5, 5))
    labels = [_approach_label(row["approach"]) for row in rows]
    values = [row["success_rate"] * 100 for row in rows]
    colors = [APPROACH_COLORS[row["approach"]] for row in rows]
    bars = ax.bar(labels, values, color=colors, width=0.58)

    ax.set_title("Skuteczność walidacji według podejścia")
    ax.set_ylabel("Poprawne wyniki [%]")
    ax.set_ylim(0, 108)
    ax.grid(axis="y", alpha=0.28)
    ax.spines[["top", "right"]].set_visible(False)

    for bar, row, value in zip(bars, rows, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{row['passed']}/{row['total']}\n{value:.1f}%",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    _save_figure(plt, fig, path)


def _plot_success_by_tier(plt: Any, rows: list[dict[str, Any]], path: Path) -> None:
    """Plot grouped success rates by approach and difficulty tier."""
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    row_by_key = {(row["approach"], row["tier"]): row for row in rows}
    x_positions = list(range(len(TIER_ORDER)))
    width = 0.24

    for approach_index, approach in enumerate(APPROACH_ORDER):
        offset = (approach_index - 1) * width
        values = [row_by_key.get((approach, tier), {"success_rate": 0})["success_rate"] * 100 for tier in TIER_ORDER]
        bars = ax.bar(
            [position + offset for position in x_positions],
            values,
            width=width,
            label=_approach_label(approach),
            color=APPROACH_COLORS[approach],
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.6,
                f"{value:.0f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_title("Skuteczność według poziomu trudności")
    ax.set_xlabel("Poziom trudności przypadku testowego")
    ax.set_ylabel("Poprawne wyniki [%]")
    ax.set_xticks(x_positions, [_tier_label(tier) for tier in TIER_ORDER])
    ax.set_ylim(0, 112)
    ax.grid(axis="y", alpha=0.28)
    ax.legend(title="Podejście", ncols=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.spines[["top", "right"]].set_visible(False)

    _save_figure(plt, fig, path)


def _plot_status_by_approach(plt: Any, rows: list[dict[str, Any]], path: Path) -> None:
    """Plot PASS/FAIL/ERR counts as stacked bars by approach."""
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    labels = [_approach_label(row["approach"]) for row in rows]
    bottoms = [0] * len(rows)

    for status in STATUS_ORDER:
        values = [_status_value(row, status) for row in rows]
        bars = ax.bar(labels, values, bottom=bottoms, color=STATUS_COLORS[status], label=STATUS_LABELS[status])
        for bar, value, bottom in zip(bars, values, bottoms):
            if value:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom + value / 2,
                    str(value),
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                )
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]

    ax.set_title("Struktura wyników walidacji")
    ax.set_ylabel("Liczba przypadków testowych")
    ax.set_ylim(0, max(bottoms) * 1.1 if bottoms else 1)
    ax.grid(axis="y", alpha=0.28)
    ax.legend(title="Wynik", ncols=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.spines[["top", "right"]].set_visible(False)

    _save_figure(plt, fig, path)


def _plot_average_costs(plt: Any, rows: list[dict[str, Any]], path: Path) -> None:
    """Plot average runtime and token usage by approach."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = [_approach_label(row["approach"]) for row in rows]
    colors = [APPROACH_COLORS[row["approach"]] for row in rows]

    _plot_metric_bars(
        axes[0],
        labels,
        [row["avg_total_time"] for row in rows],
        colors,
        "Średni czas generowania i walidacji",
        "Sekundy",
        "{:.1f}s",
    )
    _plot_metric_bars(
        axes[1],
        labels,
        [row["avg_total_tokens"] for row in rows],
        colors,
        "Średnie zużycie tokenów LLM",
        "Tokeny",
        "{:.0f}",
    )

    fig.suptitle("Koszt wykonania eksperymentu według podejścia", fontsize=15, fontweight="bold")
    _save_figure(plt, fig, path)


def _plot_errors_by_category(plt: Any, records: list[dict[str, Any]], path: Path) -> None:
    """Plot non-passing result counts by error category and approach."""
    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    labels = [_approach_label(approach) for approach in APPROACH_ORDER]
    bottoms = [0] * len(APPROACH_ORDER)
    counts = _error_category_counts(records)

    for category in ERROR_CATEGORY_ORDER:
        values = [counts[(approach, category)] for approach in APPROACH_ORDER]
        bars = ax.bar(
            labels,
            values,
            bottom=bottoms,
            color=ERROR_CATEGORY_COLORS[category],
            label=_error_category_label(category),
        )
        for bar, value, bottom in zip(bars, values, bottoms):
            if value:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom + value / 2,
                    str(value),
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                )
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]

    ax.set_title("Kategorie błędów według podejścia")
    ax.set_ylabel("Liczba niepoprawnych wyników")
    ax.set_ylim(0, max(bottoms) * 1.14 if bottoms else 1)
    ax.grid(axis="y", alpha=0.28)
    ax.legend(title="Kategoria błędu", ncols=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.spines[["top", "right"]].set_visible(False)

    _save_figure(plt, fig, path)


def _plot_typescript_errors_by_group(plt: Any, records: list[dict[str, Any]], path: Path) -> None:
    """Plot grouped TypeScript compiler error counts by approach."""
    fig, ax = plt.subplots(figsize=(12.4, 6.4))
    labels = [_approach_label(approach) for approach in APPROACH_ORDER]
    bottoms = [0] * len(APPROACH_ORDER)
    counts = _typescript_error_group_counts(records)

    for group in TYPESCRIPT_ERROR_GROUP_ORDER:
        values = [counts[(approach, group)] for approach in APPROACH_ORDER]
        if not any(values):
            continue

        bars = ax.bar(
            labels,
            values,
            bottom=bottoms,
            color=TYPESCRIPT_ERROR_GROUP_COLORS[group],
            label=_typescript_error_group_label(group),
        )
        for bar, value, bottom in zip(bars, values, bottoms):
            if value:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom + value / 2,
                    str(value),
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=9,
                    fontweight="bold",
                )
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]

    ax.set_title("Typy błędów TypeScript według podejścia")
    ax.set_ylabel("Liczba błędów kompilatora")
    ax.set_ylim(0, max(bottoms) * 1.14 if bottoms else 1)
    ax.grid(axis="y", alpha=0.28)
    ax.legend(title="Typ błędu", ncols=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.spines[["top", "right"]].set_visible(False)

    _save_figure(plt, fig, path)


def _plot_systematic_typescript_errors(plt: Any, records: list[dict[str, Any]], path: Path) -> None:
    """Plot repeated TypeScript error groups ordered by compiler error count."""
    rows = _systematic_typescript_error_rows(_typescript_error_detail_rows(records))
    fig, ax = plt.subplots(figsize=(12, 6.6))

    labels = [row["typescript_error_group_label"] for row in rows]
    values = [row["count"] for row in rows]
    colors = [TYPESCRIPT_ERROR_GROUP_COLORS[row["typescript_error_group"]] for row in rows]
    y_positions = list(range(len(rows)))
    bars = ax.barh(y_positions, values, color=colors)

    max_value = max(values) if values else 1
    for bar, row, value in zip(bars, rows, values):
        ax.text(
            value + max_value * 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{value} bł., {row['affected_records']} wyn., {row['affected_cases']} przyp.",
            va="center",
            fontsize=9,
        )

    ax.set_title("Systematyczne typy błędów TypeScript")
    ax.set_xlabel("Liczba błędów kompilatora")
    ax.set_yticks(y_positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max_value * 1.42)
    ax.grid(axis="x", alpha=0.28)
    ax.spines[["top", "right"]].set_visible(False)

    _save_figure(plt, fig, path)


def _error_category_counts(records: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    """Count non-passing results for each approach/category pair."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for approach in APPROACH_ORDER:
        for category in ERROR_CATEGORY_ORDER:
            counts[(approach, category)] = 0

    for record in records:
        category = record.get("error_category", "")
        approach = record.get("approach", "")
        if category:
            counts[(approach, category)] += 1
    return counts


def _typescript_error_group_counts(records: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    """Count TypeScript compiler errors for each approach/group pair."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for approach in APPROACH_ORDER:
        for group in TYPESCRIPT_ERROR_GROUP_ORDER:
            counts[(approach, group)] = 0

    for record in records:
        approach = record.get("approach", "")
        for error in record.get("_typescript_errors", []):
            counts[(approach, error["typescript_error_group"])] += 1
    return counts


def _plot_metric_bars(
    ax: Any,
    labels: list[str],
    values: list[float],
    colors: list[str],
    title: str,
    ylabel: str,
    label_format: str,
) -> None:
    """Plot a labeled metric bar chart on an existing axis."""
    bars = ax.bar(labels, values, color=colors, width=0.58)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.28)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylim(0, max(values) * 1.18 if values else 1)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.03,
            label_format.format(value),
            ha="center",
            va="bottom",
            fontweight="bold",
        )


def _save_figure(plt: Any, fig: Any, path: Path) -> None:
    """Save a figure as a high-resolution PNG and close it."""
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _approach_label(approach: str) -> str:
    """Return display label for an approach."""
    return APPROACH_LABELS.get(approach, approach)


def _tier_label(tier: str) -> str:
    """Return display label for a difficulty tier."""
    return TIER_LABELS.get(tier, tier)


def _error_category_label(category: str) -> str:
    """Return display label for an error category."""
    return ERROR_CATEGORY_LABELS.get(category, category)


def _typescript_error_group_label(group: str) -> str:
    """Return display label for a TypeScript error group."""
    return TYPESCRIPT_ERROR_GROUP_LABELS.get(group, group)


def _status_value(row: dict[str, Any], status: str) -> int:
    """Return the count column for a status summary row."""
    if status == "PASS":
        return int(row["passed"])
    if status == "FAIL":
        return int(row["failed"])
    return int(row["errors"])


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
    """Export CSV and chart artifacts from experiment run directories."""
    records = load_records(runs_dir, selected_run_ids)
    if not records:
        raise ValueError(f"No experiment records found in {runs_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_files = export_csvs(records, output_dir)
    chart_files = export_charts(records, output_dir)

    print(f"Exported {len(records)} records to {output_dir}")
    for label, path in csv_files.items():
        print(f"- {label}: {path}")
    for label, path in chart_files.items():
        print(f"- {label}: {path}")


def main() -> None:
    """Parse CLI arguments and export analytics artifacts."""
    parser = argparse.ArgumentParser(description="Export experiment analytics as CSV files and PNG charts.")
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
