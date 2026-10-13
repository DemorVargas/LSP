"""Tests for JSON-RPC message framing (Content-Length header protocol)."""
import json
import pytest
from src.framing import encode_message, decode_messages, FramingError


class TestEncodeMessage:
    def test_encode_simple_message(self):
        msg = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
        encoded = encode_message(msg)
        assert encoded.startswith(b"Content-Length: ")
        # Format: Content-Length: N\r\ncharset=utf-8\r\n\r\n{body}
        header_block, body = encoded.split(b"\r\n\r\n", 1)
        assert b"charset=utf-8" in header_block
        assert json.loads(body) == msg

    def test_encode_preserves_unicode(self):
        msg = {"text": "héllo wörld"}
        encoded = encode_message(msg)
        body = encoded.split(b"\r\n\r\n", 1)[1]
        assert json.loads(body) == msg

    def test_encode_includes_charset(self):
        msg = {"method": "test"}
        encoded = encode_message(msg)
        header_block = encoded.split(b"\r\n\r\n", 1)[0]
        assert b"charset=utf-8" in header_block


class TestDecodeMessages:
    def test_decode_single_message(self):
        msg = {"jsonrpc": "2.0", "method": "ping"}
        raw = encode_message(msg)
        messages, remainder = decode_messages(raw)
        assert messages == [msg]
        assert remainder == b""

    def test_decode_multiple_messages(self):
        msg1 = {"jsonrpc": "2.0", "method": "first"}
        msg2 = {"jsonrpc": "2.0", "method": "second"}
        raw = encode_message(msg1) + encode_message(msg2)
        messages, remainder = decode_messages(raw)
        assert messages == [msg1, msg2]
        assert remainder == b""

    def test_decode_partial_message_returns_empty(self):
        raw = b"Content-Length: 100\r\n\r\n{\"partial"
        messages, remainder = decode_messages(raw)
        assert messages == []
        assert remainder == raw

    def test_decode_preserves_remainder(self):
        msg = {"method": "complete"}
        raw = encode_message(msg) + b"Content-Length: 50\r\n\r\n"
        messages, remainder = decode_messages(raw)
        assert messages == [msg]
        assert remainder == b"Content-Length: 50\r\n\r\n"

    def test_decode_invalid_content_length_raises(self):
        raw = b"Content-Length: abc\r\n\r\n{}"
        with pytest.raises(FramingError):
            decode_messages(raw)

    def test_decode_missing_header_raises(self):
        raw = b"Invalid-Header: 5\r\n\r\n{}"
        with pytest.raises(FramingError):
            decode_messages(raw)

    def test_decode_empty_input(self):
        messages, remainder = decode_messages(b"")
        assert messages == []
        assert remainder == b""

    def test_decode_incremental(self):
        """Feed data in small chunks, should reassemble correctly."""
        msg = {"jsonrpc": "2.0", "method": "test", "params": {"key": "value"}}
        raw = encode_message(msg)
        messages = []
        remainder = b""
        for i in range(0, len(raw), 5):
            chunk = raw[i:i+5]
            new_msgs, remainder = decode_messages(remainder + chunk)
            messages.extend(new_msgs)
        assert messages == [msg]
