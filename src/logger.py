"""Structured logging system for the LSP server."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, TextIO


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class StructuredFormatter:
    """Formats log records as JSON-serializable dicts."""

    def format(self, record: dict[str, Any]) -> dict[str, Any]:
        return record


class Logger:
    """Multi-handler structured logger with level filtering."""

    def __init__(self, level: LogLevel = LogLevel.INFO, stream: TextIO | None = None):
        self._level = level
        self._handlers: list[TextIO] = []
        self._formatter = StructuredFormatter()
        if stream is not None:
            self._handlers.append(stream)

    def is_enabled_for(self, level: LogLevel) -> bool:
        return level >= self._level

    def set_level(self, level: LogLevel) -> None:
        self._level = level

    def add_handler(self, stream: TextIO) -> None:
        if stream not in self._handlers:
            self._handlers.append(stream)

    def remove_handler(self, stream: TextIO) -> None:
        if stream in self._handlers:
            self._handlers.remove(stream)

    def _emit(self, level: LogLevel, message: str, context: dict[str, Any] | None = None,
              source: dict[str, Any] | None = None) -> None:
        if not self.is_enabled_for(level):
            return
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.name,
            "message": message,
            "module": "minilsp",
        }
        if context is not None:
            record["context"] = context
        if source is not None:
            record["source"] = source
        formatted = self._formatter.format(record)
        line = json.dumps(formatted, ensure_ascii=False)
        for handler in self._handlers:
            try:
                handler.write(line + "\n")
                handler.flush()
            except Exception:
                pass

    def debug(self, message: str, context: dict[str, Any] | None = None,
              source: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.DEBUG, message, context, source)

    def info(self, message: str, context: dict[str, Any] | None = None,
             source: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.INFO, message, context, source)

    def warning(self, message: str, context: dict[str, Any] | None = None,
                source: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.WARNING, message, context, source)

    def error(self, message: str, context: dict[str, Any] | None = None,
              source: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.ERROR, message, context, source)

    def critical(self, message: str, context: dict[str, Any] | None = None,
                 source: dict[str, Any] | None = None) -> None:
        self._emit(LogLevel.CRITICAL, message, context, source)
