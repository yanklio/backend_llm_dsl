# NestJS AI Generator

AI-powered code generation framework that transforms natural language descriptions into production-ready NestJS applications with TypeORM integration.

## Overview

This project compares three generation pipelines for automated NestJS backend creation, serving as the experimental framework for a master's thesis on AI-assisted code generation.

```
Natural Language
      |
      v
  LLM Provider (Groq / Gemini / OpenRouter / Ollama)
      |
      +---> DSL Pipeline:   NL → YAML Blueprint → Jinja2 Templates → NestJS Code
      +---> Raw Pipeline:   NL → LLM File Map (JSON) → Direct Output → NestJS Code
      +---> Mixed Pipeline: NL → YAML Blueprint → LLM File Map (Blueprint-guided) → NestJS Code
      |
      v
  Validation (TypeScript syntax + npm build + runtime)
      |
      v
  Experiment Analytics (CSV export + charts)
```

## Pipelines

| Pipeline | Flow | Determinism |
|----------|------|-------------|
| **DSL** | Natural language → YAML blueprint → Jinja2 template rendering | High — templates enforce structure |
| **Raw** | Natural language → LLM generates full file map directly | Low — LLM has full freedom |
| **Mixed** | Natural language → YAML blueprint → LLM uses blueprint to generate file map | Medium — blueprint constrains output |

## Quick Start

```bash
# Generate a NestJS project from a description
python main.py "Create a blog API with users and posts"

# Or run a full experiment batch
python -m src.experiments.runner --approach all --provider openrouter
python -m src.experiments.analysis --results results/test_results.json
python -m src.experiments.export_analytics
```

## Project Structure

```
src/
  dsl/          # DSL engine — Jinja2 templates, YAML loader, textual DSL compiler
  llm/          # LLM integration — provider wrappers, prompt templates, response parsing
  experiments/  # Thesis experiment runner, analysis, and analytics export
  validators/   # TypeScript syntax & runtime validation
  shared/       # Shared config, logging, exceptions, template helpers
results/        # Benchmark inputs (test_cases.yaml), generated outputs, analytics
examples/       # Sample textual DSL and blueprint files
templates/      # Jinja2 templates for NestJS code generation
```

## Tech Stack

- **Python 3.9+**: Core framework
- **LangChain**: Multi-provider LLM abstraction (Groq, Gemini, OpenRouter, Ollama)
- **Jinja2**: Template rendering for NestJS code generation
- **PyYAML**: Blueprint parsing and serialization
- **Ruff**: Python linting and formatting
- **pytest + coverage**: Testing with 70%+ coverage target

The generated output is a full NestJS application using TypeORM, class-validator, and Swagger.
