"""Error types shared by the textual DSL compiler stages."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    """Location of a syntactic element in the textual DSL source."""

    line: int
    column: int


class TextualDSLError(Exception):
    """Base exception for textual DSL compiler errors."""

    def __init__(
        self,
        message: str,
        location: SourceLocation | None = None,
        code: str | None = None,
    ) -> None:
        """Initialize a compiler error."""
        self.message = message
        self.location = location
        self.code = code
        super().__init__(self.__str__())

    def __str__(self) -> str:
        """Return a stable human-readable error message."""
        prefix = f"[{self.code}] " if self.code else ""
        if self.location is None:
            return f"{prefix}{self.message}"
        return (
            f"{prefix}{self.message} "
            f"at {self.location.line}:{self.location.column}"
        )


class LexError(TextualDSLError):
    """Raised when the lexer encounters an unknown character."""


class ParseError(TextualDSLError):
    """Raised when textual DSL syntax is invalid."""


class ResolveError(TextualDSLError):
    """Raised when textual DSL semantic validation fails."""
