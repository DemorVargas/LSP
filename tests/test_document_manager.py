"""Tests for the in-memory document manager."""
import pytest
from src.document_manager import DocumentManager
from src.types import Position, Range, TextDocumentItem


@pytest.fixture
def dm():
    return DocumentManager()


@pytest.fixture
def sample_doc():
    return TextDocumentItem(
        uri="file:///test.py",
        language_id="python",
        version=1,
        text="def hello():\n    print('world')\n",
    )


class TestDocumentManager:
    def test_open_document(self, dm, sample_doc):
        dm.open_document(sample_doc)
        assert dm.get_text(sample_doc.uri) == sample_doc.text
        assert dm.get_version(sample_doc.uri) == 1

    def test_open_replaces_existing(self, dm, sample_doc):
        dm.open_document(sample_doc)
        updated = TextDocumentItem(
            uri=sample_doc.uri,
            language_id="python",
            version=2,
            text="new text",
        )
        dm.open_document(updated)
        assert dm.get_text(sample_doc.uri) == "new text"
        assert dm.get_version(sample_doc.uri) == 2

    def test_close_document(self, dm, sample_doc):
        dm.open_document(sample_doc)
        dm.close_document(sample_doc.uri)
        assert dm.get_text(sample_doc.uri) is None

    def test_get_missing_document_returns_none(self, dm):
        assert dm.get_text("file:///nonexistent.py") is None

    def test_apply_full_text_change(self, dm, sample_doc):
        dm.open_document(sample_doc)
        dm.apply_change(sample_doc.uri, None, "completely new")
        assert dm.get_text(sample_doc.uri) == "completely new"

    def test_apply_incremental_change(self, dm, sample_doc):
        dm.open_document(sample_doc)
        # Replace 'hello' with 'goodbye'
        change = {
            "range": {"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 9}},
            "text": "goodbye",
        }
        dm.apply_change(sample_doc.uri, change["range"], change["text"])
        result = dm.get_text(sample_doc.uri)
        assert "goodbye" in result
        assert "hello" not in result

    def test_apply_change_at_position(self, dm, sample_doc):
        dm.open_document(sample_doc)
        # Insert at line 1, character 4
        change = {
            "range": {"start": {"line": 1, "character": 4}, "end": {"line": 1, "character": 4}},
            "text": "# comment\n    ",
        }
        dm.apply_change(sample_doc.uri, change["range"], change["text"])
        lines = dm.get_text(sample_doc.uri).split("\n")
        assert lines[1].strip() == "# comment"

    def test_get_word_at_position(self, dm, sample_doc):
        dm.open_document(sample_doc)
        word = dm.get_word_at(Position(0, 6))
        assert word == "hello"

    def test_get_word_at_non_word(self, dm, sample_doc):
        dm.open_document(sample_doc)
        word = dm.get_word_at(Position(0, 3))
        assert word is None

    def test_get_line(self, dm, sample_doc):
        dm.open_document(sample_doc)
        line = dm.get_line(sample_doc.uri, 0)
        assert line == "def hello():"

    def test_get_line_out_of_range(self, dm, sample_doc):
        dm.open_document(sample_doc)
        assert dm.get_line(sample_doc.uri, 99) is None

    def test_position_at_offset(self, dm, sample_doc):
        dm.open_document(sample_doc)
        # "def " is 4 chars, so offset 4 is line 0, char 4
        pos = dm.position_at_offset(sample_doc.uri, 4)
        assert pos == Position(0, 4)

    def test_offset_at_position(self, dm, sample_doc):
        dm.open_document(sample_doc)
        # "def hello():" = 12 chars, +\n = 13, so line 1 char 4 = offset 17
        offset = dm.offset_at_position(sample_doc.uri, Position(1, 4))
        assert offset == 17

    def test_document_exists(self, dm, sample_doc):
        assert not dm.has_document(sample_doc.uri)
        dm.open_document(sample_doc)
        assert dm.has_document(sample_doc.uri)

    def test_get_all_documents(self, dm, sample_doc):
        dm.open_document(sample_doc)
        docs = dm.get_all_documents()
        assert sample_doc.uri in docs
