# Results Workspace

This directory contains thesis experiment inputs, outputs, logs, and analytics.
The `tests/` directory is reserved for automated tests of the pipeline code.

## Structure

- `test_cases.yaml`: benchmark cases used by DSL, Raw, and Mixed runs
- `base_nest_project/`: NestJS scaffold copied before each generation attempt
- `generated_blueprints/`: intermediate DSL and Mixed YAML blueprints
- `runs/`: timestamped run folders with `metadata.json`, `results.json`, and per-record JSON files
- `archives/`: archived smoke, aborted, or contaminated runs
- `analytics/`: exported CSV summaries and PNG charts
- `test_results.json`: aggregate result file updated by the runner
- `experiments_debug.log`: detailed suppressed stdout/stderr from generation and validation

## Common Commands

Run experiments:

```bash
python -m src.experiments.runner --approach all --provider openrouter
```

Analyze a run:

```bash
python -m src.experiments.analysis --results results/runs/<run_id>/results.json
```

Export analytics:

```bash
python -m src.experiments.export_analytics
```
