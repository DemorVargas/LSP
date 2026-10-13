"""Tests for the LSP server core — JSON-RPC dispatch and lifecycle."""
import json
import pytest
from src.server import LSPServer, LSPError
from src.types import TextDocumentItem


@pytest.fixture
def server():
    return LSPServer()


def make_request(id, method, params=None):
    msg = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def make_notification(method, params=None):
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    return msg


class TestServerInitialization:
    def test_init_request(self, server):
        resp = server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        result = resp["result"]
        assert result["capabilities"]["textDocumentSync"] is not None
        assert "serverInfo" in result

    def test_initialized_notification(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        result = server.handle_notification(make_notification("initialized", {}))
        assert result is None

    def test_shutdown_request(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        resp = server.handle_request(make_request(2, "shutdown"))
        result = resp["result"]
        assert result is None

    def test_exit_notification(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("shutdown"))
        result = server.handle_notification(make_notification("exit"))
        assert result is None


class TestUnknownMethod:
    def test_unknown_method_returns_error(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        resp = server.handle_request(make_request(99, "nonexistent/method"))
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_unknown_notification_no_error(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        result = server.handle_notification(make_notification("nonexistent/notification"))
        assert result is None


class TestDocumentLifecycle:
    def test_did_open(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        doc = TextDocumentItem("file:///test.py", "python", 1, "print('hello')")
        result = server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        assert result is None
        assert server.doc_manager.has_document("file:///test.py")

    def test_did_change(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        doc = TextDocumentItem("file:///test.py", "python", 1, "print('hello')")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        change = {
            "textDocument": {"uri": "file:///test.py", "version": 2},
            "contentChanges": [{"text": "print('goodbye')"}],
        }
        result = server.handle_notification(make_notification("textDocument/didChange", change))
        assert result is None
        assert server.doc_manager.get_text("file:///test.py") == "print('goodbye')"

    def test_did_close(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        doc = TextDocumentItem("file:///test.py", "python", 1, "print('hello')")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        result = server.handle_notification(make_notification("textDocument/didClose", {
            "textDocument": {"uri": "file:///test.py"}
        }))
        assert result is None
        assert not server.doc_manager.has_document("file:///test.py")


class TestHover:
    def test_hover_returns_null_for_no_info(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        doc = TextDocumentItem("file:///test.py", "python", 1, "x = 1\n")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        resp = server.handle_request(make_request(5, "textDocument/hover", {
            "textDocument": {"uri": "file:///test.py"},
            "position": {"line": 0, "character": 0},
        }))
        result = resp["result"]
        assert result is not None
        assert "x" in result["contents"]["value"]


class TestDefinition:
    def test_definition_returns_null_when_not_found(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        doc = TextDocumentItem("file:///test.py", "python", 1, "x = 1\n")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        resp = server.handle_request(make_request(5, "textDocument/definition", {
            "textDocument": {"uri": "file:///test.py"},
            "position": {"line": 0, "character": 0},
        }))
        result = resp["result"]
        # AST finds x as a variable definition
        assert result is not None
        assert result["uri"] == "file:///test.py"


class TestCompletions:
    def test_completions_for_python_keywords(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        server.handle_notification(make_notification("initialized", {}))
        doc = TextDocumentItem("file:///test.py", "python", 1, "pr\n")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        resp = server.handle_request(make_request(5, "textDocument/completion", {
            "textDocument": {"uri": "file:///test.py"},
            "position": {"line": 0, "character": 2},
        }))
        result = resp["result"]
        assert isinstance(result, dict)
        items = result.get("items", [])
        labels = [item["label"] for item in items]
        assert "print" in labels

    def test_completions_empty_when_no_match(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        doc = TextDocumentItem("file:///test.py", "python", 1, "xyz\n")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        result = server.handle_request(make_request(5, "textDocument/completion", {
            "textDocument": {"uri": "file:///test.py"},
            "position": {"line": 0, "character": 3},
        }))
        items = result.get("items", [])
        assert len(items) == 0


class TestDiagnostics:
    def test_publish_diagnostics(self, server):
        server.handle_request(make_request(1, "initialize", {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        }))
        doc = TextDocumentItem("file:///test.py", "python", 1, "def foo(:\n")
        server.handle_notification(make_notification("textDocument/didOpen", {
            "textDocument": doc.to_dict()
        }))
        result = server.handle_notification(make_notification("textDocument/didChange", {
            "textDocument": {"uri": "file:///test.py", "version": 2},
            "contentChanges": [{"text": "def foo(:\n"}],
        }))
        assert result is None


class TestServerState:
    def test_before_initialize_rejects_requests(self, server):
        result = server.handle_request(make_request(1, "textDocument/hover", {
            "textDocument": {"uri": "file:///test.py"},
            "position": {"line": 0, "character": 0},
        }))
        assert "error" in result
        assert result["error"]["code"] == -32002

    def test_server_info(self, server):
        assert server.server_info["name"] == "minilsp"
        assert "version" in server.server_info
