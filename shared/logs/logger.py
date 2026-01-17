import sys
from enum import Enum


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

    # Class-level configuration
    _verbose = False  # Controls verbosity of output
    _min_level = LogLevel.INFO  # Minimum log level to display

    # Level hierarchy for filtering
    LEVEL_HIERARCHY = {
        LogLevel.DEBUG: 0,
        LogLevel.INFO: 1,
        LogLevel.WARNING: 2,
        LogLevel.SUCCESS: 2,
        LogLevel.ERROR: 3,
        LogLevel.START: 1,
        LogLevel.END: 1,
    }

    # Formatting symbols
    SYMBOLS = {
        LogLevel.START: "▶",
        LogLevel.END: "◀",
        LogLevel.SUCCESS: "✓",
        LogLevel.ERROR: "✗",
        LogLevel.WARNING: "⚠",
        LogLevel.INFO: "ℹ",
        LogLevel.DEBUG: "◆",
    }

    @classmethod
    def set_verbose(cls, verbose: bool):
        """Enable/disable verbose logging."""
        cls._verbose = verbose

    @classmethod
    def set_min_level(cls, level: LogLevel):
        """Set minimum log level to display."""
        cls._min_level = level

    @classmethod
    def _should_log(cls, level: LogLevel) -> bool:
        """Check if a message at this level should be logged."""
        if cls._verbose:
            return True
        return cls.LEVEL_HIERARCHY.get(level, 1) >= cls.LEVEL_HIERARCHY.get(cls._min_level, 1)

    @classmethod
    def _format_message(cls, level: LogLevel, message: str) -> str:
        """Format a log message with symbol and level."""
        symbol = cls.SYMBOLS.get(level, "•")

        if level == LogLevel.START:
            return f"{symbol} {message}"
        elif level == LogLevel.END:
            return f"{symbol} {message}"
        elif level == LogLevel.SUCCESS:
            return f"{symbol} {message}"
        elif level == LogLevel.ERROR:
            return f"{symbol} {message}"
        elif level == LogLevel.WARNING:
            return f"{symbol} {message}"
        elif level == LogLevel.INFO:
            return f"{symbol} {message}"
        elif level == LogLevel.DEBUG:
            return f"{symbol} {message}"

        return message

    @classmethod
    def log(cls, level: LogLevel, message: str):
        """Log a message at the specified level."""
        if not cls._should_log(level):
            return

        formatted = cls._format_message(level, message)
        print(formatted)

    @classmethod
    def start(cls, message: str):
        """Log start of an operation."""
        cls.log(LogLevel.START, message)

    @classmethod
    def end(cls, message: str):
        """Log end of an operation."""
        cls.log(LogLevel.END, message)

    @classmethod
    def success(cls, message: str):
        """Log a success message."""
        cls.log(LogLevel.SUCCESS, message)

    @classmethod
    def error(cls, message: str):
        """Log an error message."""
        cls.log(LogLevel.ERROR, message)
        sys.stderr.flush()

    @classmethod
    def warn(cls, message: str):
        """Log a warning message."""
        cls.log(LogLevel.WARNING, message)

    @classmethod
    def info(cls, message: str):
        """Log an info message."""
        cls.log(LogLevel.INFO, message)

    @classmethod
    def debug(cls, message: str):
        """Log a debug message (only in verbose mode)."""
        if cls._verbose:
            cls.log(LogLevel.DEBUG, message)


# Create a default instance for convenience
logger = UnifiedLogger

__all__ = ["UnifiedLogger", "logger", "LogLevel"]
