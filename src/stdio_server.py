"""Stdio transport for LSP — reads JSON-RPC from stdin, writes to stdout."""
from __future__ import annotations
import asyncio
import json
import sys
from typing import Any

from src.framing import encode_message, decode_messages, FramingError
from src.server import LSPServer


class StdioTransport:
    def __init__(self, reader: asyncio.StreamReader | None = None, writer: asyncio.StreamWriter | None = None):
        self._reader = reader or asyncio.StreamReader()
        self._writer = writer
        self._buffer = b""

    def _decode_one(self, data: bytes) -> tuple[dict[str, Any] | None, bytes]:
        """Decode exactly one message. Returns (message, remainder)."""
        header_end = data.find(b"\r\n\r\n")
        if header_end == -1:
            return None, data
        header_block = data[:header_end].decode("ascii")
        content_length = None
        for line in header_block.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    raise FramingError(f"Invalid Content-Length header: {line}")
                break
        if content_length is None:
            raise FramingError("Missing Content-Length header")
        body_start = header_end + 4
        body_end = body_start + content_length
        if len(data) < body_end:
            return None, data
        body = data[body_start:body_end]
        try:
            msg = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise FramingError(f"Invalid JSON body: {e}")
        return msg, data[body_end:]

    async def read_message(self) -> dict[str, Any] | None:
        """Read a single LSP message from stdin. Returns None on EOF."""
        while True:
            # Try to decode one message from buffer
            try:
                msg, remainder = self._decode_one(self._buffer)
            except FramingError:
                # Malicious or corrupt frame — drop connection
                return None
            if msg is not None:
                self._buffer = remainder
                return msg
            # Need more data
            try:
                chunk = await self._reader.read(4096)
            except (ConnectionResetError, BrokenPipeError):
                return None
            if not chunk:
                # EOF — try one last decode
                try:
                    msg, remainder = self._decode_one(self._buffer)
                except FramingError:
                    return None
                if msg is not None:
                    self._buffer = remainder
                    return msg
                return None
            self._buffer += chunk

    async def write_message(self, msg: dict[str, Any]) -> None:
        """Write a single LSP message to stdout."""
        data = encode_message(msg)
        if self._writer is None:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        else:
            self._writer.write(data)
            await self._writer.drain()


async def run_server() -> None:
    """Main entry point — run the LSP server over stdio."""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    transport = StdioTransport(reader=reader)
    server = LSPServer()
    server.set_notification_callback(lambda msg: asyncio.create_task(transport.write_message(msg)))

    while True:
        msg = await transport.read_message()
        if msg is None:
            break
        if "id" in msg and "method" in msg:
            # Request
            response = server.handle_request(msg)
            await transport.write_message(response)
        elif "method" in msg:
            # Notification
            server.handle_notification(msg)
        # Responses from client (id + result/error) are ignored for now
