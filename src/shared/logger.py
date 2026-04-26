"""Project-wide logger with simple level-based formatting."""

import sys
from enum import Enum

DEFAULT_LOG_SYMBOL = "•"


class LogLevel(Enum):
    """Log level enumeration."""

    START = "START"
    END = "END"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class UnifiedLogger:
    """Unified logger for all project modules."""

    LEVEL_HIERARCHY = {
        LogLevel.DEBUG: 0,
        LogLevel.INFO: 1,
        LogLevel.WARNING: 2,
        LogLevel.SUCCESS: 2,
        LogLevel.ERROR: 3,
        LogLevel.START: 1,
        LogLevel.END: 1,
    }

    SYMBOLS = {
        LogLevel.START: "▶",
        LogLevel.END: "◀",
        LogLevel.SUCCESS: "✓",
        LogLevel.ERROR: "✗",
        LogLevel.WARNING: "⚠",
        LogLevel.INFO: "ℹ",
        LogLevel.DEBUG: "◆",
    }
    _verbose = False
    _min_level = LogLevel.INFO

    @classmethod
    def set_verbose(cls, verbose: bool) -> None:
        """Enable/disable verbose logging."""
        cls._verbose = verbose

    @classmethod
    def set_min_level(cls, level: LogLevel) -> None:
        """Set minimum log level to display."""
        cls._min_level = level

    @classmethod
    def _level_rank(cls, level: LogLevel) -> int:
        """Return the numeric rank for a log level."""
        return cls.LEVEL_HIERARCHY.get(level, 1)

    @classmethod
    def _should_log(cls, level: LogLevel) -> bool:
        """Check if a message at this level should be logged."""
        if cls._verbose:
            return True
        return cls._level_rank(level) >= cls._level_rank(cls._min_level)

    @classmethod
    def _format_message(cls, level: LogLevel, message: str) -> str:
        """Format a log message with symbol and level."""
        symbol = cls.SYMBOLS.get(level, DEFAULT_LOG_SYMBOL)
        return f"{symbol} {message}"

    @classmethod
    def log(cls, level: LogLevel, message: str) -> None:
        """Log a message at the specified level."""
        if not cls._should_log(level):
            return

        formatted = cls._format_message(level, message)
        print(formatted)

    @classmethod
    def _log_at_level(cls, level: LogLevel, message: str) -> None:
        """Log a message at a fixed level."""
        cls.log(level, message)

    @classmethod
    def start(cls, message: str) -> None:
        """Log start of an operation."""
        cls._log_at_level(LogLevel.START, message)

    @classmethod
    def end(cls, message: str) -> None:
        """Log end of an operation."""
        cls._log_at_level(LogLevel.END, message)

    @classmethod
    def success(cls, message: str) -> None:
        """Log a success message."""
        cls._log_at_level(LogLevel.SUCCESS, message)

    @classmethod
    def error(cls, message: str) -> None:
        """Log an error message."""
        cls._log_at_level(LogLevel.ERROR, message)
        sys.stderr.flush()

    @classmethod
    def warn(cls, message: str) -> None:
        """Log a warning message."""
        cls._log_at_level(LogLevel.WARNING, message)

    @classmethod
    def info(cls, message: str) -> None:
        """Log an info message."""
        cls._log_at_level(LogLevel.INFO, message)

    @classmethod
    def debug(cls, message: str) -> None:
        """Log a debug message (only in verbose mode)."""
        if cls._verbose:
            cls._log_at_level(LogLevel.DEBUG, message)


logger = UnifiedLogger

__all__ = ["UnifiedLogger", "logger", "LogLevel"]
