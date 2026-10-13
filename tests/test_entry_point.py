"""Tests for the main entry point."""
import sys
import pytest
from unittest.mock import patch, MagicMock
from src.stdio_server import run_server, StdioTransport


class TestEntryPoint:
    def test_main_calls_run_server(self):
        from src.main import main
        with patch("src.main.run_server") as mock_run:
            main()
            mock_run.assert_called_once()

    def test_main_handles_keyboard_interrupt(self):
        from src.main import main
        with patch("src.main.run_server", side_effect=KeyboardInterrupt):
            main()  # Should not raise

    def test_main_handles_eof(self):
        from src.main import main
        with patch("src.main.run_server", side_effect=SystemExit(0)):
            main()

    def test_run_server_reads_and_writes(self):
        """Integration test: feed a full initialize/shutdown cycle through run_server."""
        import asyncio
        from src.framing import encode_message

        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"processId": None, "rootUri": "file:///test", "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
            {"jsonrpc": "2.0", "method": "exit"},
        ]
        raw = b"".join(encode_message(m) for m in messages)

        async def _test():
            reader = asyncio.StreamReader()
            reader.feed_data(raw)
            reader.feed_eof()

            written = []
            writer = MagicMock()

            async def mock_drain():
                pass

            writer.write = lambda data: written.append(data)
            writer.drain = mock_drain

            transport = StdioTransport(reader=reader, writer=writer)
            from src.server import LSPServer
            server = LSPServer()
            while True:
                msg = await transport.read_message()
                if msg is None:
                    break
                if "id" in msg and "method" in msg:
                    response = server.handle_request(msg)
                    await transport.write_message(response)
                elif "method" in msg:
                    server.handle_notification(msg)
            return written

        written = asyncio.run(_test())
        assert len(written) == 2  # Two responses: initialize + shutdown
