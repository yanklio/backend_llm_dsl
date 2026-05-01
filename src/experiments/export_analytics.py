"""Export experiment results to CSV files and thesis charts."""

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
APPROACH_LABELS = {"dsl": "DSL", "raw": "Raw", "mixed": "Mixed"}
TIER_LABELS = {"simple": "Proste", "medium": "Średnie", "complex": "Złożone"}
STATUS_LABELS = {"PASS": "Poprawne", "FAIL": "Niepoprawne", "ERR": "Błąd generacji"}
STATUS_COLORS = {"PASS": "#2E7D32", "FAIL": "#EF6C00", "ERR": "#C62828"}
APPROACH_COLORS = {"dsl": "#1565C0", "raw": "#6A1B9A", "mixed": "#00897B"}


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
    }

    _plot_success_by_approach(plt, approach_rows, files["success_by_approach"])
    _plot_success_by_tier(plt, approach_tier_rows, files["success_by_tier"])
    _plot_status_by_approach(plt, approach_rows, files["status_by_approach"])
    _plot_average_costs(plt, approach_rows, files["average_costs"])
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
        values = [row_by_key[(approach, tier)]["success_rate"] * 100 for tier in TIER_ORDER]
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
