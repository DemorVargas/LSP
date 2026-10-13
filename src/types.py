"""LSP protocol data types."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class DiagnosticSeverity(IntEnum):
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class CompletionItemKind(IntEnum):
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    KEYWORD = 14


class SymbolKind(IntEnum):
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18


class InsertTextFormat(IntEnum):
    PLAIN_TEXT = 1
    SNIPPET = 2


@dataclass(frozen=True, order=True)
class Position:
    line: int
    character: int

    def to_dict(self) -> dict[str, int]:
        return {"line": self.line, "character": self.character}

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> Position:
        return cls(line=d["line"], character=d["character"])


@dataclass(frozen=True)
class Range:
    start: Position
    end: Position

    def contains(self, pos: Position) -> bool:
        return self.start <= pos <= self.end

    def __contains__(self, pos: Position) -> bool:
        return self.contains(pos)

    def is_empty(self) -> bool:
        return self.start == self.end

    def to_dict(self) -> dict[str, dict[str, int]]:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}

    @classmethod
    def from_dict(cls, d: dict[str, dict[str, int]]) -> Range:
        return cls(start=Position.from_dict(d["start"]), end=Position.from_dict(d["end"]))


@dataclass(frozen=True)
class Location:
    uri: str
    range: Range

    def to_dict(self) -> dict[str, Any]:
        return {"uri": self.uri, "range": self.range.to_dict()}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Location:
        return cls(uri=d["uri"], range=Range.from_dict(d["range"]))


@dataclass
class Diagnostic:
    range: Range
    message: str
    severity: DiagnosticSeverity | None = None
    code: int | str | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"range": self.range.to_dict(), "message": self.message}
        if self.severity is not None:
            d["severity"] = int(self.severity)
        if self.code is not None:
            d["code"] = self.code
        if self.source is not None:
            d["source"] = self.source
        return d


@dataclass
class TextDocumentItem:
    uri: str
    language_id: str
    version: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"uri": self.uri, "languageId": self.language_id, "version": self.version, "text": self.text}


@dataclass
class CompletionItem:
    label: str
    kind: CompletionItemKind | None = None
    detail: str | None = None
    documentation: str | None = None
    insert_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"label": self.label}
        if self.kind is not None:
            d["kind"] = int(self.kind)
        if self.detail is not None:
            d["detail"] = self.detail
        if self.documentation is not None:
            d["documentation"] = self.documentation
        if self.insert_text is not None:
            d["insertText"] = self.insert_text
        return d


@dataclass
class SymbolInformation:
    name: str
    kind: SymbolKind
    location: Location
    container_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "kind": int(self.kind), "location": self.location.to_dict()}
        if self.container_name is not None:
            d["containerName"] = self.container_name
        return d


@dataclass
class DocumentSymbol:
    name: str
    kind: SymbolKind
    range: Range
    selection_range: Range
    detail: str | None = None
    children: list[DocumentSymbol] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "kind": int(self.kind),
            "range": self.range.to_dict(),
            "selectionRange": self.selection_range.to_dict(),
        }
        if self.detail is not None:
            d["detail"] = self.detail
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass(frozen=True)
class TextEdit:
    range: Range
    new_text: str

    def to_dict(self) -> dict[str, Any]:
        return {"range": self.range.to_dict(), "newText": self.new_text}


@dataclass(frozen=True)
class ParameterInformation:
    label: str
    documentation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"label": self.label}
        if self.documentation is not None:
            d["documentation"] = self.documentation
        return d


@dataclass(frozen=True)
class SignatureInformation:
    label: str
    parameters: list[ParameterInformation] = field(default_factory=list)
    documentation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"label": self.label}
        if self.parameters:
            d["parameters"] = [p.to_dict() for p in self.parameters]
        if self.documentation is not None:
            d["documentation"] = self.documentation
        return d


@dataclass(frozen=True)
class TextDocumentIdentifier:
    uri: str

    def to_dict(self) -> dict[str, str]:
        return {"uri": self.uri}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> TextDocumentIdentifier:
        return cls(uri=d["uri"])
