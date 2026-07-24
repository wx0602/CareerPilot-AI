from __future__ import annotations

import json
import logging
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .config import Settings


request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = request_id_context.get()
        return True


class JsonFormatter(logging.Formatter):
    _reserved = set(logging.makeLogRecord({}).__dict__) | {
        "message",
        "asctime",
        "request_id",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in self._reserved:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        request_id = getattr(record, "request_id", request_id_context.get())
        event = getattr(record, "event", "-")
        message = f"{timestamp} | {record.levelname:<7} | {request_id} | {event} | {record.getMessage()}"
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return message


def _mark_handler(handler: logging.Handler) -> logging.Handler:
    handler.addFilter(RequestContextFilter())
    setattr(handler, "_careerpilot_handler", True)
    return handler


def configure_logging(settings: Settings) -> logging.Logger:
    logger = logging.getLogger("careerpilot")
    logger.disabled = False
    logger.setLevel(getattr(logging, settings.log_level))
    logger.propagate = False
    for name, candidate in logging.root.manager.loggerDict.items():
        if name.startswith("careerpilot.") and isinstance(candidate, logging.Logger):
            candidate.disabled = False

    for handler in list(logger.handlers):
        if getattr(handler, "_careerpilot_handler", False):
            logger.removeHandler(handler)
            handler.close()

    console = _mark_handler(logging.StreamHandler())
    console.setFormatter(ConsoleFormatter())
    logger.addHandler(console)

    if settings.log_to_file:
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = _mark_handler(
            RotatingFileHandler(
                log_dir / "app.log",
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
                encoding="utf-8",
            )
        )
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)

    return logger


def bind_request_id(request_id: str) -> Token[str]:
    return request_id_context.set(request_id)


def reset_request_id(token: Token[str]) -> None:
    request_id_context.reset(token)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger("careerpilot" if not name else f"careerpilot.{name}")
