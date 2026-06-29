"""Structured logging configuration for CLI and API workflows."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Minimal JSON formatter for machine-readable logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "context") and isinstance(record.context, dict):
            payload["context"] = record.context
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(service_name: str) -> None:
    """Configure root logger once, with optional JSON mode via LOG_FORMAT=json."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text").lower()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s [service=%(service_name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )

    class ServiceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.service_name = service_name
            return True

    handler.addFilter(ServiceFilter())
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
