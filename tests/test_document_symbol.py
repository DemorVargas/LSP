"""Tests for document symbol and diagnostics features."""
import pytest
from src.server import LSPServer
from src.types import TextDocumentItem


@pytest.fixture
def server():
    s = LSPServer()
    s.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"processId": None, "rootUri": "file:///test", "capabilities": {}},
    })
    s.handle_notification({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    return s


def open_doc(server, text, uri="file:///test.py"):
    doc = TextDocumentItem(uri, "python", 1, text)
    server.handle_notification({
        "jsonrpc": "2.0", "method": "textDocument/didOpen",
        "params": {"textDocument": doc.to_dict()},
    })


class TestDocumentSymbol:
    def test_empty_document_returns_empty_list(self, server):
        open_doc(server, "")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        assert result["result"] == []

    def test_finds_function(self, server):
        open_doc(server, "def my_func():\n    pass\n")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        symbols = result["result"]
        assert len(symbols) == 1
        assert symbols[0]["name"] == "my_func"
        assert symbols[0]["kind"] == 12  # SymbolKind.FUNCTION

    def test_finds_class(self, server):
        open_doc(server, "class MyClass:\n    pass\n")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        symbols = result["result"]
        assert len(symbols) == 1
        assert symbols[0]["name"] == "MyClass"
        assert symbols[0]["kind"] == 5  # SymbolKind.CLASS

    def test_finds_multiple_symbols(self, server):
        text = "class Foo:\n    def bar(self):\n        pass\n\ndef baz():\n    pass\n"
        open_doc(server, text)
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        symbols = result["result"]
        names = [s["name"] for s in symbols]
        assert "Foo" in names
        assert "baz" in names
        # Methods are children of their class, not top-level
        foo = [s for s in symbols if s["name"] == "Foo"][0]
        assert "bar" in [c["name"] for c in foo.get("children", [])]

    def test_function_with_args(self, server):
        open_doc(server, "def func(a, b, c):\n    return a + b + c\n")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        symbols = result["result"]
        assert symbols[0]["name"] == "func"

    def test_class_with_inheritance(self, server):
        open_doc(server, "class Child(Base):\n    pass\n")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        symbols = result["result"]
        assert symbols[0]["name"] == "Child"

    def test_no_symbols_in_plain_text(self, server):
        open_doc(server, "x = 1\ny = 2\n")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        # Variables are symbols too
        names = [s["name"] for s in result["result"]]
        assert "x" in names
        assert "y" in names

    def test_symbol_location(self, server):
        open_doc(server, "def located():\n    pass\n")
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.py"}},
        })
        sym = result["result"][0]
        assert sym["location"]["uri"] == "file:///test.py"
        assert sym["location"]["range"]["start"]["line"] == 0

    def test_document_not_found_returns_empty(self, server):
        result = server.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///nonexistent.py"}},
        })
        assert result["result"] == []


class TestDiagnostics:
    def test_publishes_diagnostics_on_open(self, server):
        doc = TextDocumentItem("file:///test.py", "python", 1, "def foo(:\n")
        published = []
        server._publish_diagnostics = lambda uri: published.append(uri)
        server.handle_notification({
            "jsonrpc": "2.0", "method": "textDocument/didOpen",
            "params": {"textDocument": doc.to_dict()},
        })
        assert "file:///test.py" in published

    def test_publishes_diagnostics_on_change(self, server):
        open_doc(server, "x = 1\n")
        published = []
        server._publish_diagnostics = lambda uri: published.append(uri)
        server.handle_notification({
            "jsonrpc": "2.0", "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "file:///test.py", "version": 2},
                "contentChanges": [{"text": "def bar(:\n"}],
            },
        })
        assert "file:///test.py" in published

    def test_trailing_open_paren_detected(self, server):
        open_doc(server, "def foo(\n")
        diagnostics = server._get_diagnostics("file:///test.py")
        assert len(diagnostics) > 0
        # AST syntax error takes precedence
        assert diagnostics[0]["severity"] == 1  # ERROR

    def test_trailing_comma_detected(self, server):
        open_doc(server, "x = 1,\n")
        diagnostics = server._get_diagnostics("file:///test.py")
        assert len(diagnostics) > 0

    def test_clean_code_no_diagnostics(self, server):
        open_doc(server, "def foo():\n    return 42\n")
        diagnostics = server._get_diagnostics("file:///test.py")
        assert len(diagnostics) == 0

    def test_multiple_issues(self, server):
        open_doc(server, "def foo(\nclass Bar,\n")
        diagnostics = server._get_diagnostics("file:///test.py")
        assert len(diagnostics) >= 2
