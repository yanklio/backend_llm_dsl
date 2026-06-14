"""Type mappings used by DSL template rendering."""

TS_TYPE_MAP = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "date": "Date",
    "enum": "string",
}
DEFAULT_TS_TYPE = "any"


def to_ts_type(source_type: str) -> str:
    """Map a DSL field type to its TypeScript type."""
    return TS_TYPE_MAP.get(source_type, DEFAULT_TS_TYPE)
