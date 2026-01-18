def to_ts_type(py_type: str) -> str:
    """Converts a simple Python type to a TypeScript type.

    Args:
        py_type (str): The Python type string (e.g., 'string', 'number').

    Returns:
        str: The corresponding TypeScript type.
    """
    if py_type == "string":
        return "string"
    if py_type == "number":
        return "number"
    if py_type == "boolean":
        return "boolean"
    if py_type == "enum":
        return "string"
    return "any"
