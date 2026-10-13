"""Tests for LSP protocol data types."""
from src.types import (
    Position, Range, Location, Diagnostic, DiagnosticSeverity,
    TextDocumentItem, CompletionItem, CompletionItemKind,
    SymbolInformation, SymbolKind, TextDocumentIdentifier,
    DocumentSymbol, TextEdit, InsertTextFormat,
)


class TestPosition:
    def test_position_equality(self):
        p1 = Position(line=0, character=5)
        p2 = Position(line=0, character=5)
        assert p1 == p2

    def test_position_ordering(self):
        """Positions compare line first, then character."""
        assert Position(0, 5) < Position(1, 0)
        assert Position(0, 5) < Position(0, 6)
        assert Position(0, 5) == Position(0, 5)

    def test_position_dict_roundtrip(self):
        p = Position(line=10, character=20)
        d = p.to_dict()
        assert d == {"line": 10, "character": 20}
        assert Position.from_dict(d) == p


class TestRange:
    def test_range_contains_position(self):
        r = Range(Position(0, 5), Position(10, 5))
        assert Position(5, 0) in r
        assert Position(0, 5) in r
        assert Position(10, 5) in r

    def test_range_excludes_outside(self):
        r = Range(Position(0, 5), Position(10, 5))
        assert Position(0, 4) not in r
        assert Position(11, 0) not in r

    def test_range_empty(self):
        r = Range(Position(3, 3), Position(3, 3))
        assert r.is_empty()

    def test_range_dict_roundtrip(self):
        r = Range(Position(1, 2), Position(3, 4))
        d = r.to_dict()
        assert d == {"start": {"line": 1, "character": 2}, "end": {"line": 3, "character": 4}}
        assert Range.from_dict(d) == r


class TestLocation:
    def test_location_creation(self):
        loc = Location("file:///test.py", Range(Position(0, 0), Position(0, 5)))
        assert loc.uri == "file:///test.py"
        assert loc.range.start.line == 0

    def test_location_dict_roundtrip(self):
        loc = Location("file:///test.py", Range(Position(1, 2), Position(3, 4)))
        d = loc.to_dict()
        assert d == {"uri": "file:///test.py", "range": {"start": {"line": 1, "character": 2}, "end": {"line": 3, "character": 4}}}
        assert Location.from_dict(d) == loc


class TestDiagnostic:
    def test_diagnostic_creation(self):
        d = Diagnostic(
            range=Range(Position(0, 0), Position(0, 5)),
            message="Undefined variable",
            severity=DiagnosticSeverity.ERROR,
        )
        assert d.message == "Undefined variable"
        assert d.severity == DiagnosticSeverity.ERROR

    def test_diagnostic_dict(self):
        d = Diagnostic(
            range=Range(Position(2, 3), Position(2, 8)),
            message="Warning",
            severity=DiagnosticSeverity.WARNING,
        )
        result = d.to_dict()
        assert result["message"] == "Warning"
        assert result["severity"] == 2  # WARNING


class TestTextDocumentItem:
    def test_creation(self):
        doc = TextDocumentItem(
            uri="file:///test.py",
            language_id="python",
            version=1,
            text="print('hello')",
        )
        assert doc.language_id == "python"
        assert doc.version == 1


class TestCompletionItem:
    def test_creation(self):
        item = CompletionItem(
            label="print",
            kind=CompletionItemKind.FUNCTION,
            detail="builtin function",
        )
        assert item.label == "print"
        assert item.kind == CompletionItemKind.FUNCTION


class TestSymbolInformation:
    def test_creation(self):
        sym = SymbolInformation(
            name="MyClass",
            kind=SymbolKind.CLASS,
            location=Location("file:///test.py", Range(Position(0, 0), Position(10, 0))),
        )
        assert sym.name == "MyClass"
        assert sym.kind == SymbolKind.CLASS


class TestDocumentSymbol:
    def test_creation(self):
        ds = DocumentSymbol(
            name="my_function",
            kind=SymbolKind.FUNCTION,
            range=Range(Position(0, 0), Position(5, 0)),
            selection_range=Range(Position(0, 4), Position(0, 16)),
        )
        assert ds.name == "my_function"
        assert ds.selection_range.start.character == 4


class TestTextEdit:
    def test_creation(self):
        edit = TextEdit(
            range=Range(Position(0, 0), Position(0, 5)),
            new_text="hello",
        )
        assert edit.new_text == "hello"

    def test_replace_entire_line(self):
        edit = TextEdit(
            range=Range(Position(3, 0), Position(3, 10)),
            new_text="pass",
        )
        assert edit.range.start.line == 3
        assert edit.new_text == "pass"


class TestTextDocumentIdentifier:
    def test_creation(self):
        td = TextDocumentIdentifier(uri="file:///main.py")
        assert td.uri == "file:///main.py"

    def test_dict(self):
        td = TextDocumentIdentifier(uri="file:///main.py")
        assert td.to_dict() == {"uri": "file:///main.py"}
