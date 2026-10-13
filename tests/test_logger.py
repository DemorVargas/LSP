"""Tests for structured logging system."""
import pytest
import json
import sys
from io import StringIO
from src.logger import Logger, LogLevel, StructuredFormatter


class TestLogLevel:
    def test_levels_exist(self):
        assert LogLevel.DEBUG == 0
        assert LogLevel.INFO == 1
        assert LogLevel.WARNING == 2
    def test_critical_level(self):
        assert LogLevel.CRITICAL == 4


class TestStructuredFormatter:
    def test_format_basic(self):
        formatter = StructuredFormatter()
        record = {
            "timestamp": "2024-01-01T00:00:00",
            "level": "INFO",
            "message": "test message",
            "module": "test",
        }
        result = formatter.format(record)
        assert isinstance(result, dict)
        assert result["level"] == "INFO"
        assert result["message"] == "test message"
        assert result["module"] == "test"

    def test_format_includes_source(self):
        formatter = StructuredFormatter()
        record = {
            "timestamp": "2024-01-01T00:00:00",
            "level": "INFO",
            "message": "test",
            "module": "test",
            "source": {"file": "test.py", "line": 42, "function": "main"},
        }
        result = formatter.format(record)
        assert result["source"]["file"] == "test.py"
        assert result["source"]["line"] == 42

    def test_format_json_serializable(self):
        formatter = StructuredFormatter()
        record = {
            "timestamp": "2024-01-01T00:00:00",
            "level": "INFO",
            "message": "test",
            "module": "test",
            "context": {"uri": "file:///test.py"},
        }
        result = formatter.format(record)
        # Must be JSON serializable
        json_str = json.dumps(result)
        assert json_str is not None


class TestLogger:
    def test_debug_not_emitted_at_info_level(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.debug("debug msg")
        output = stream.getvalue()
        assert "debug msg" not in output

    def test_info_emitted(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.info("info msg")
        output = stream.getvalue()
        assert "info msg" in output

    def test_warning_emitted(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.warning("warn msg")
        output = stream.getvalue()
        assert "warn msg" in output

    def test_error_emitted(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.error("error msg")
        output = stream.getvalue()
        assert "error msg" in output

    def test_critical_emitted(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.critical("critical msg")
        output = stream.getvalue()
        assert "critical msg" in output

    def test_debug_emitted_at_debug_level(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.DEBUG, stream=stream)
        logger.debug("debug msg")
        output = stream.getvalue()
        assert "debug msg" in output

    def test_context_included(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.info("msg", context={"uri": "file:///test.py"})
        output = stream.getvalue()
        assert "file:///test.py" in output

    def test_multiple_handlers(self):
        stream1 = StringIO()
        stream2 = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream1)
        logger.add_handler(stream2)
        logger.info("msg")
        assert "msg" in stream1.getvalue()
        assert "msg" in stream2.getvalue()

    def test_remove_handler(self):
        stream1 = StringIO()
        stream2 = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream1)
        logger.add_handler(stream2)
        logger.remove_handler(stream2)
        logger.info("msg")
        assert "msg" in stream1.getvalue()
        assert "msg" not in stream2.getvalue()

    def test_set_level(self):
        stream = StringIO()
        logger = Logger(level=LogLevel.INFO, stream=stream)
        logger.set_level(LogLevel.WARNING)
        logger.info("info msg")
        assert "info msg" not in stream.getvalue()
        logger.warning("warn msg")
        assert "warn msg" in stream.getvalue()

    def test_is_enabled_for(self):
        logger = Logger(level=LogLevel.INFO)
        assert logger.is_enabled_for(LogLevel.INFO)
        assert logger.is_enabled_for(LogLevel.WARNING)
        assert not logger.is_enabled_for(LogLevel.DEBUG)
