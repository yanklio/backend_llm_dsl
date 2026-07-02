# Packages

These package facades document and enforce the intended architecture boundary:

```text
Textual DSL ─┐
YAML DSL ────┼→ normalized IR → NestJS backend
LLM output ──┘
```

## Boundaries

- `dsl_core`: textual DSL frontend only. No LLM calls. No NestJS templates.
- `intermediate_representation`: normalized blueprint-compatible IR loading and validation.
- `generator_nestjs`: NestJS backend generation from IR-compatible input.
- `validator`: generated backend validation.
- `llm_providers`: optional LLM integration for `from-prompt` and benchmark workflows.

The current implementation still lives in `src/`; these facades make the target
architecture explicit while keeping the refactor low-risk.
