"""Redact secrets from log messages before they are written or served."""

from __future__ import annotations

import logging
import re

# Google AI Studio keys, Alpaca keys, Finnhub tokens, generic query params.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"(?<=[?&]key=)[^&\s'\"]+", re.IGNORECASE),
    re.compile(r"(?<=[?&]token=)[^&\s'\"]+", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?[^'\"\s&]+"),
)

_REDACTED = "***REDACTED***"


def sanitize_log_message(text: str) -> str:
    """Remove API keys and tokens from a log line or exception message."""
    if not text:
        return text
    sanitized = text
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(_REDACTED, sanitized)
    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts secrets from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)
        if record.args:
            record.args = tuple(
                sanitize_log_message(arg) if isinstance(arg, str) else arg for arg in record.args
            )
        if record.exc_info:
            record.exc_text = None
        return True
