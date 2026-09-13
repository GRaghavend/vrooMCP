"""
Structured JSON logging for the Car Buying Advisor backend.

Every log line is a single JSON object so it can be grepped/parsed later
instead of scrolled through. A request_id (set per HTTP request by FastAPI
middleware, once that exists) is attached automatically to every log line
emitted during that request via a contextvar -- callers never have to pass
it explicitly.

Usage:
    from logging_config import setup_logging, get_logger, log_event

    setup_logging()  # call once, at process startup
    logger = get_logger(__name__)
    log_event(logger, logging.INFO, "tool.call.start", tool="get_brand_stats", arguments={"brand_name": "BMW"})
"""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import time
from pathlib import Path
from typing import Any

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# Set by request-handling code (FastAPI middleware later; tests can set it
# directly) so every log line emitted while handling a request is tagged
# without passing request_id through every function call.
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        fields = getattr(record, "fields", None)
        if fields:
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO, log_filename: str = "app.log") -> None:
    """Configure root logging once at process startup. Idempotent.

    Each OS process logs to its own file (pass a distinct `log_filename`):
    two independent RotatingFileHandler instances rotating the *same* file
    from separate processes can race and corrupt output, so the MCP
    tool-server subprocess uses "mcp_server.log" while the orchestrator
    process uses "app.log".
    """
    LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. re-imported in tests)

    root.setLevel(level)
    formatter = JsonFormatter()

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / log_filename, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Emit one structured log line: `event` is the short machine-readable
    name (e.g. "tool.call.end"), fields are arbitrary structured context."""
    logger.log(level, event, extra={"fields": fields})


def truncate(value: Any, max_len: int = 200) -> Any:
    """Shorten long strings before they hit a log line (e.g. review text)."""
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + f"... [{len(value)} chars total]"
    return value


class timed:
    """Context manager returning elapsed milliseconds on exit via .ms"""

    def __enter__(self) -> "timed":
        self._start = time.perf_counter()
        self.ms = 0.0
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.ms = round((time.perf_counter() - self._start) * 1000, 2)
