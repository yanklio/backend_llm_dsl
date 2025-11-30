def to_ts_type(py_type):
    """Converts a simple Python type to a TypeScript type."""
    if py_type == "string":
        return "string"
    if py_type == "number":
        return "number"
    if py_type == "boolean":
        return "boolean"
    if py_type == "enum":
        return "string"
    return "any"
