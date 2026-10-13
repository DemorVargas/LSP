"""Tests for hard limits in the framing layer — DoS protection."""
import json
import pytest
from src.framing import encode_message, decode_messages, FramingError


# Limits enforced by the framing layer
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
MAX_HEADER_SIZE = 8192                  # 8 KB


class TestContentLengthCap:
    def test_reject_content_length_over_max(self):
        """Content-Length exceeding the hard cap must be refused."""
        body = b"x" * 100
        raw = b"Content-Length: " + str(MAX_CONTENT_LENGTH + 1).encode() + b"\r\n\r\n" + body
        with pytest.raises(FramingError):
            decode_messages(raw)

    def test_accept_content_length_at_max(self):
        """Content-Length exactly at the cap is allowed."""
        body = b"x" * 100
        raw = b"Content-Length: " + str(MAX_CONTENT_LENGTH).encode() + b"\r\n\r\n" + body
        messages, remainder = decode_messages(raw)
        assert len(messages) == 0  # body incomplete, that's fine

    def test_reject_content_length_way_over(self):
        """Absurd Content-Length values must be refused immediately."""
        raw = b"Content-Length: 99999999999999\r\n\r\n{}"
        with pytest.raises(FramingError):
            decode_messages(raw)


class TestHeaderSizeCap:
    def test_reject_header_with_huge_field(self):
        """A header block exceeding the size cap must be refused."""
        huge = b"X" * (MAX_HEADER_SIZE + 1)
        raw = huge + b"\r\n\r\n{}"
        with pytest.raises(FramingError):
            decode_messages(raw)

    def test_accept_header_at_cap(self):
        """A header block right at the cap is allowed."""
        # Build a header with padding comments at exactly the cap
        padding_len = MAX_HEADER_SIZE - len(b"Content-Length: 2\r\n\r\n")
        header = b"Content-Length: 2\r\nX-Pad: " + b"p" * (padding_len - len(b"X-Pad: ")) + b"\r\n\r\n"
        assert len(header) <= MAX_HEADER_SIZE + 64  # small slack for framing
        messages, _ = decode_messages(header + b"{}")
        assert messages == [{}]

    def test_normal_header_far_under_cap(self):
        """Normal messages pass through untouched."""
        msg = {"jsonrpc": "2.0", "method": "ping"}
        raw = encode_message(msg)
        messages, remainder = decode_messages(raw)
        assert messages == [msg]
        assert remainder == b""


class TestBufferGrowthCap:
    def test_discard_buffer_when_header_incomplete_and_oversized(self):
        """If we've buffered more than the cap without a complete header, refuse."""
        raw = b"Content-Length: 1000000\r\nX-Comment: " + b"c" * (MAX_HEADER_SIZE + 100)
        with pytest.raises(FramingError):
            decode_messages(raw)

    def test_normal_partial_message_kept_in_buffer(self):
        """Incomplete normal messages are buffered, not discarded."""
        msg = {"jsonrpc": "2.0", "method": "ping"}
        raw = encode_message(msg)
        messages, remainder = decode_messages(raw[:20])
        assert messages == []
        assert len(remainder) > 0  # buffered for next call


class TestEncodingStillWorks:
    def test_round_trip_unchanged(self):
        """Full round trip after hardening must produce identical results."""
        for msg in [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {"uri": "file:///a.py", "languageId": "python", "version": 1, "text": "x = 1"}}},
            {"jsonrpc": "2.0", "id": 2, "result": {"capabilities": {}}},
            {"jsonrpc": "2.0", "id": 3, "error": {"code": -32601, "message": "Method not found"}},
        ]:
            raw = encode_message(msg)
            messages, remainder = decode_messages(raw)
            assert messages == [msg]
            assert remainder == b""

    def test_unicode_round_trip(self):
        msg = {"jsonrpc": "2.0", "method": "тест", "params": {"значение": "данные"}}
        raw = encode_message(msg)
        messages, _ = decode_messages(raw)
        assert messages == [msg]

    def test_multiple_messages_one_buffer(self):
        raw = encode_message({"jsonrpc": "2.0", "id": 1, "method": "a"}) + encode_message({"jsonrpc": "2.0", "id": 2, "method": "b"})
        messages, remainder = decode_messages(raw)
        assert len(messages) == 2
        assert remainder == b""
