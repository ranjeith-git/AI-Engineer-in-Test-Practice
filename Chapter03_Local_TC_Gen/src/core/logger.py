"""Logging setup.

Guarantees that credential *values* never reach the log file: we only log the
engine name, latency, and outcome. A defensive filter redacts known secret
values in case a message ever carries them.
"""

import logging
import sys

from .paths import LOG_PATH

# Names of values that must never appear in a log line.
_SECRET_VALUE_NAMES = {
    "api_token",
    "apikey",
    "api_key",
    "token",
    "email",
    "password",
    "secret",
    "authorization",
    "cookie",
}


class _SecretRedactionFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self._known_values: set[str] = set()

    def remember_secret(self, value: str) -> None:
        """Register a live credential value so it can be redacted."""
        if value:
            self._known_values.add(value)

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._known_values:
            return True
        try:
            msg = record.getMessage()
        except Exception:
            return True
        redacted = msg
        for value in self._known_values:
            if value in redacted:
                redacted = redacted.replace(value, "[REDACTED]")
        if redacted != msg:
            record.msg = redacted
            record.args = ()
        return True


_secret_filter = _SecretRedactionFilter()


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("tcgen")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_secret_filter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_secret_filter)
    logger.addHandler(stream_handler)

    return logger


def remember_secret(value: str) -> None:
    """Register a credential value for redaction in all future log lines."""
    if value:
        _secret_filter.remember_secret(value)


def get_logger() -> logging.Logger:
    return configure_logging()
