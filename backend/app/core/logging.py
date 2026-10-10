import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_object: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request_id if available in record or contextvar
        req_id = getattr(record, "request_id", None)
        if not req_id:
            try:
                from app.middleware.request_id import request_id_ctx

                req_id = request_id_ctx.get()
            except ImportError:
                pass

        if req_id:
            log_object["request_id"] = req_id

        # Include exception info if present
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        # Include extra attributes
        extra_keys = set(record.__dict__.keys()) - {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "request_id",
        }
        for key in extra_keys:
            log_object[key] = getattr(record, key)

        return json.dumps(log_object)


def setup_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """Configure structured logging for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)

    if environment.lower() == "production":
        stream_handler.setFormatter(JSONFormatter())
    else:
        # Development readable format with JSON extra fields
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        stream_handler.setFormatter(formatter)

    root_logger.addHandler(stream_handler)

    # Quiet external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
