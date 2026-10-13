"""Tests for the stdio transport layer."""
import asyncio
import pytest
from src.stdio_server import StdioTransport, run_server


class TestStdioTransport:
    @pytest.mark.asyncio
    async def test_read_message(self):
        transport = StdioTransport()
        # Simulate a complete LSP message
        import json
        msg = {"jsonrpc": "2.0", "method": "test"}
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        raw = header + body
        # Mock stdin
        transport._reader = asyncio.StreamReader()
        transport._reader.feed_data(raw)
        transport._reader.feed_eof()
        result = await transport.read_message()
        assert result == msg

    @pytest.mark.asyncio
    async def test_read_multiple_messages(self):
        transport = StdioTransport()
        import json
        msg1 = {"jsonrpc": "2.0", "method": "first"}
        msg2 = {"jsonrpc": "2.0", "method": "second"}
        raw = b""
        for msg in [msg1, msg2]:
            body = json.dumps(msg).encode("utf-8")
            raw += f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
        transport._reader = asyncio.StreamReader()
        transport._reader.feed_data(raw)
        transport._reader.feed_eof()
        result1 = await transport.read_message()
        result2 = await transport.read_message()
        assert result1 == msg1
        assert result2 == msg2

    @pytest.mark.asyncio
    async def test_read_eof_returns_none(self):
        transport = StdioTransport()
        transport._reader = asyncio.StreamReader()
        transport._reader.feed_eof()
        result = await transport.read_message()
        assert result is None

    @pytest.mark.asyncio
    async def test_write_message(self):
        transport = StdioTransport()
        import json
        msg = {"jsonrpc": "2.0", "result": {"ok": True}}
        body = json.dumps(msg).encode("utf-8")
        expected = f"Content-Length: {len(body)}\r\ncharset=utf-8\r\n\r\n".encode("ascii") + body
        from src.framing import encode_message
        assert encode_message(msg) == expected

    @pytest.mark.asyncio
    async def test_incremental_read(self):
        transport = StdioTransport()
        import json
        msg = {"jsonrpc": "2.0", "method": "test", "params": {"key": "value"}}
        body = json.dumps(msg).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        raw = header + body
        # Feed data byte by byte
        transport._reader = asyncio.StreamReader()
        for byte in raw:
            transport._reader.feed_data(bytes([byte]))
        transport._reader.feed_eof()
        result = await transport.read_message()
        assert result == msg
