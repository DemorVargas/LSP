"""In-memory document manager for LSP."""
from __future__ import annotations
import re
from typing import Any

from src.types import Position, TextDocumentItem


class DocumentManager:
    def __init__(self):
        self._docs: dict[str, TextDocumentItem] = {}

    def open_document(self, doc: TextDocumentItem) -> None:
        self._docs[doc.uri] = doc

    def close_document(self, uri: str) -> None:
        self._docs.pop(uri, None)

    def get_text(self, uri: str) -> str | None:
        doc = self._docs.get(uri)
        return doc.text if doc else None

    def get_version(self, uri: str) -> int | None:
        doc = self._docs.get(uri)
        return doc.version if doc else None

    def has_document(self, uri: str) -> bool:
        return uri in self._docs

    def get_all_documents(self) -> dict[str, TextDocumentItem]:
        return dict(self._docs)

    def apply_change(self, uri: str, change_range: dict[str, Any] | None, new_text: str) -> None:
        doc = self._docs.get(uri)
        if doc is None:
            return
        if change_range is None:
            doc.text = new_text
            return
        start = change_range["start"]
        end = change_range["end"]
        start_offset = self.offset_at_position(uri, Position(start["line"], start["character"]))
        end_offset = self.offset_at_position(uri, Position(end["line"], end["character"]))
        text = doc.text
        doc.text = text[:start_offset] + new_text + text[end_offset:]

    def get_line(self, uri: str, line: int) -> str | None:
        text = self.get_text(uri)
        if text is None:
            return None
        lines = text.split("\n")
        if line < 0 or line >= len(lines):
            return None
        return lines[line]

    def get_word_at(self, pos: Position, uri: str = "file:///test.py") -> str | None:
        line = self.get_line(uri, pos.line)
        if line is None:
            return None
        if pos.character >= len(line):
            return None
        if not line[pos.character].isalnum() and line[pos.character] != "_":
            return None
        start = pos.character
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1
        end = pos.character
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1
        return line[start:end]

    def position_at_offset(self, uri: str, offset: int) -> Position:
        text = self.get_text(uri)
        if text is None:
            return Position(0, 0)
        text = text[:offset]
        line = text.count("\n")
        last_nl = text.rfind("\n")
        character = offset if last_nl == -1 else offset - last_nl - 1
        return Position(line, character)

    def offset_at_position(self, uri: str, pos: Position) -> int:
        text = self.get_text(uri)
        if text is None:
            return 0
        lines = text.split("\n")
        offset = 0
        for i in range(min(pos.line, len(lines))):
            offset += len(lines[i]) + 1
        offset += min(pos.character, len(lines[pos.line]) if pos.line < len(lines) else 0)
        return offset
