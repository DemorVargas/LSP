"""LSP server core — JSON-RPC dispatch, lifecycle, and feature handlers."""
from __future__ import annotations
import re
from typing import Any, Callable

from src.document_manager import DocumentManager
from src.ast_parser import parse_source, SymbolKind as ASTSymbolKind
from src.complexity import analyze_complexity, ComplexityReport, FunctionComplexity
from src.type_inference import infer_types, TypeInfo, InferenceResult
from src.lru_cache import LRUCache
from src.logger import Logger, LogLevel
from src.config import Config
from src.types import (
    Position, Range, Location, Diagnostic, DiagnosticSeverity,
    TextDocumentItem, CompletionItem, CompletionItemKind,
    SymbolInformation, SymbolKind, TextDocumentIdentifier,
    SignatureInformation, ParameterInformation,
)

# ── Python builtins for completion ──────────────────────────────────────────
PYTHON_BUILTINS = [
    ("print", CompletionItemKind.FUNCTION),
    ("len", CompletionItemKind.FUNCTION),
    ("range", CompletionItemKind.FUNCTION),
    ("enumerate", CompletionItemKind.FUNCTION),
    ("zip", CompletionItemKind.FUNCTION),
    ("map", CompletionItemKind.FUNCTION),
    ("filter", CompletionItemKind.FUNCTION),
    ("sorted", CompletionItemKind.FUNCTION),
    ("reversed", CompletionItemKind.FUNCTION),
    ("isinstance", CompletionItemKind.FUNCTION),
    ("issubclass", CompletionItemKind.FUNCTION),
    ("hasattr", CompletionItemKind.FUNCTION),
    ("getattr", CompletionItemKind.FUNCTION),
    ("setattr", CompletionItemKind.FUNCTION),
    ("open", CompletionItemKind.FUNCTION),
    ("str", CompletionItemKind.CLASS),
    ("int", CompletionItemKind.CLASS),
    ("float", CompletionItemKind.CLASS),
    ("list", CompletionItemKind.CLASS),
    ("dict", CompletionItemKind.CLASS),
    ("set", CompletionItemKind.CLASS),
    ("tuple", CompletionItemKind.CLASS),
    ("bool", CompletionItemKind.CLASS),
    ("type", CompletionItemKind.FUNCTION),
    ("id", CompletionItemKind.FUNCTION),
    ("input", CompletionItemKind.FUNCTION),
    ("abs", CompletionItemKind.FUNCTION),
    ("min", CompletionItemKind.FUNCTION),
    ("max", CompletionItemKind.FUNCTION),
    ("sum", CompletionItemKind.FUNCTION),
    ("any", CompletionItemKind.FUNCTION),
    ("all", CompletionItemKind.FUNCTION),
    ("repr", CompletionItemKind.FUNCTION),
]

PYTHON_KEYWORDS = [
    "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
    "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "None", "True", "False",
]


class LSPError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class LSPServer:
    def __init__(self):
        self.doc_manager = DocumentManager()
        self.server_info = {"name": "minilsp", "version": "0.2.0"}
        self._initialized = False
        self._shutdown = False
        self._root_uri: str | None = None
        self._client_capabilities: dict = {}
        self._notification_callback: Callable[[dict], None] | None = None
        self._ast_cache: dict[str, Any] = {}  # uri -> ParseResult

        self._request_handlers: dict[str, Any] = {
            "initialize": self._handle_initialize,
            "shutdown": self._handle_shutdown,
            "textDocument/hover": self._handle_hover,
            "textDocument/definition": self._handle_definition,
            "textDocument/completion": self._handle_completion,
            "textDocument/documentSymbol": self._handle_document_symbol,
            "textDocument/signatureHelp": self._handle_signature_help,
            "textDocument/typeInference": self._handle_type_inference,
            "textDocument/complexityAnalysis": self._handle_complexity_analysis,
        }
        self._notification_handlers: dict[str, Any] = {
            "initialized": self._handle_initialized,
            "exit": self._handle_exit,
            "textDocument/didOpen": self._handle_did_open,
            "textDocument/didChange": self._handle_did_change,
            "textDocument/didClose": self._handle_did_close,
        }

    def set_notification_callback(self, callback: Callable[[dict], None]) -> None:
        """Set a callback for sending notifications to the client."""
        self._notification_callback = callback

    # ── Public API ──────────────────────────────────────────────────────────

    def handle_request(self, msg: dict) -> dict:
        method = msg.get("method", "")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if not self._initialized and method != "initialize":
            return self._error_response(msg_id, -32002, "Server not initialized")

        if self._shutdown and method != "exit":
            return self._error_response(msg_id, -32600, "Server is shutting down")

        handler = self._request_handlers.get(method)
        if handler is None:
            return self._error_response(msg_id, -32601, f"Method not found: {method}")

        try:
            result = handler(params)
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except LSPError as e:
            return self._error_response(msg_id, e.code, e.message)
        except Exception as e:
            return self._error_response(msg_id, -32603, f"Internal error: {e}")

    def handle_notification(self, msg: dict) -> None:
        method = msg.get("method", "")
        params = msg.get("params", {})

        if not self._initialized and method not in ("initialized", "exit"):
            return

        handler = self._notification_handlers.get(method)
        if handler is None:
            return

        try:
            handler(params)
        except Exception:
            pass

    # ── Lifecycle handlers ──────────────────────────────────────────────────

    def _handle_initialize(self, params: dict) -> dict:
        self._root_uri = params.get("rootUri")
        self._client_capabilities = params.get("capabilities", {})
        return {
            "capabilities": {
                "textDocumentSync": {
                    "openClose": True,
                    "change": 2,  # Incremental
                },
                "hoverProvider": True,
                "definitionProvider": True,
                "completionProvider": {"triggerCharacters": [".", "("]},
                "documentSymbolProvider": True,
                "signatureHelpProvider": {"triggerCharacters": ["(", ","]},
                "typeInferenceProvider": True,
                "complexityAnalysisProvider": True,
            },
            "serverInfo": self.server_info,
        }

    def _handle_initialized(self, params: dict) -> None:
        self._initialized = True

    def _handle_shutdown(self, params: dict) -> None:
        self._shutdown = True
        return None

    def _handle_exit(self, params: dict) -> None:
        pass

    # ── Document lifecycle ──────────────────────────────────────────────────

    def _handle_did_open(self, params: dict) -> None:
        td = params["textDocument"]
        doc = TextDocumentItem(
            uri=td["uri"],
            language_id=td["languageId"],
            version=td["version"],
            text=td["text"],
        )
        self.doc_manager.open_document(doc)
        self._update_ast(doc.uri)
        self._publish_diagnostics(doc.uri)

    def _handle_did_change(self, params: dict) -> None:
        uri = params["textDocument"]["uri"]
        version = params["textDocument"]["version"]
        for change in params.get("contentChanges", []):
            if "range" in change:
                self.doc_manager.apply_change(uri, change["range"], change["text"])
            else:
                self.doc_manager.apply_change(uri, None, change["text"])
        doc = self.doc_manager._docs.get(uri)
        if doc:
            doc.version = version
        self._update_ast(uri)
        self._publish_diagnostics(uri)

    def _handle_did_close(self, params: dict) -> None:
        uri = params["textDocument"]["uri"]
        self.doc_manager.close_document(uri)
        self._ast_cache.pop(uri, None)

    # ── AST Management ──────────────────────────────────────────────────────

    def _update_ast(self, uri: str) -> None:
        """Re-parse a document and cache the result."""
        text = self.doc_manager.get_text(uri)
        if text is not None:
            self._ast_cache[uri] = parse_source(text)

    def _get_ast(self, uri: str):
        """Get cached AST result, parsing if needed."""
        if uri not in self._ast_cache:
            self._update_ast(uri)
        return self._ast_cache.get(uri)

    # ── Feature handlers ───────────────────────────────────────────────────

    def _handle_hover(self, params: dict) -> dict | None:
        uri = params["textDocument"]["uri"]
        pos = Position(
            line=params["position"]["line"],
            character=params["position"]["character"],
        )
        ast_result = self._get_ast(uri)
        if ast_result is None:
            return None

        # Find the most specific symbol at this position
        best = None
        for sym in ast_result.symbols:
            if sym.line_start <= pos.line <= sym.line_end:
                if best is None or (sym.line_end - sym.line_start) < (best.line_end - best.line_start):
                    best = sym

        if best is None:
            # Fall back to word-based hover
            word = self.doc_manager.get_word_at(pos, uri)
            if word:
                return {"contents": {"kind": "plaintext", "value": word}}
            return None

        # Build hover content from AST symbol
        contents = []
        if best.kind in (ASTSymbolKind.FUNCTION, ASTSymbolKind.METHOD):
            params_str = ", ".join(best.params)
            async_prefix = "async " if best.is_async else ""
            returns_str = f" -> {best.returns}" if best.returns else ""
            contents.append(f"{async_prefix}def {best.name}({params_str}){returns_str}")
        elif best.kind == ASTSymbolKind.CLASS:
            bases_str = f"({', '.join(best.bases)})" if best.bases else ""
            contents.append(f"class {best.name}{bases_str}")
        elif best.kind == ASTSymbolKind.VARIABLE:
            if best.type_annotation:
                contents.append(f"{best.name}: {best.type_annotation}")
            else:
                contents.append(best.name)

        if best.doc:
            contents.append("")
            contents.append(best.doc)

        return {"contents": {"kind": "markdown", "value": "\n\n".join(contents)}}

    def _handle_definition(self, params: dict) -> dict | list | None:
        uri = params["textDocument"]["uri"]
        pos = Position(
            line=params["position"]["line"],
            character=params["position"]["character"],
        )
        ast_result = self._get_ast(uri)
        if ast_result is None:
            return None

        # Find the word at the position
        word = self.doc_manager.get_word_at(pos, uri)
        if not word:
            return None

        # Look up the symbol in the AST
        sym = ast_result.find_symbol(word)
        if sym is None:
            return None

        return Location(uri, Range(
            Position(sym.line_start, sym.col_start),
            Position(sym.line_end, sym.col_end),
        )).to_dict()

    def _handle_completion(self, params: dict) -> dict:
        uri = params["textDocument"]["uri"]
        pos = Position(
            line=params["position"]["line"],
            character=params["position"]["character"],
        )
        ast_result = self._get_ast(uri)
        word = self.doc_manager.get_word_at(pos, uri) or ""

        items = []

        # Add scope-aware names from AST
        if ast_result is not None:
            scope_names = ast_result.get_names_in_scope(pos.line)
            for name in scope_names:
                if name.startswith(word) and name != word:
                    items.append(CompletionItem(label=name, kind=CompletionItemKind.VARIABLE).to_dict())

        # Add Python builtins
        for name, kind in PYTHON_BUILTINS:
            if name.startswith(word):
                items.append(CompletionItem(label=name, kind=kind).to_dict())

        # Add Python keywords
        for kw in PYTHON_KEYWORDS:
            if kw.startswith(word):
                items.append(CompletionItem(label=kw, kind=CompletionItemKind.KEYWORD).to_dict())

        # Deduplicate by label
        seen = set()
        unique_items = []
        for item in items:
            if item["label"] not in seen:
                seen.add(item["label"])
                unique_items.append(item)

        return {"items": unique_items, "isIncomplete": False}

    def _handle_document_symbol(self, params: dict) -> list:
        uri = params["textDocument"]["uri"]
        ast_result = self._get_ast(uri)
        if ast_result is None:
            return []

        kind_map = {
            ASTSymbolKind.FUNCTION: SymbolKind.FUNCTION,
            ASTSymbolKind.CLASS: SymbolKind.CLASS,
            ASTSymbolKind.VARIABLE: SymbolKind.VARIABLE,
            ASTSymbolKind.METHOD: SymbolKind.METHOD,
        }

        def sym_to_dict(sym):
            lsp_kind = kind_map.get(sym.kind, SymbolKind.VARIABLE)
            d = SymbolInformation(
                name=sym.name,
                kind=lsp_kind,
                location=Location(uri, Range(
                    Position(sym.line_start, sym.col_start),
                    Position(sym.line_end, sym.col_end),
                )),
            ).to_dict()
            if sym.children:
                d["children"] = [sym_to_dict(c) for c in sym.children]
            return d

        return [sym_to_dict(s) for s in ast_result.symbols if s.parent is None]

    def _handle_signature_help(self, params: dict) -> dict | None:
        """Provide signature help when user is inside a function call."""
        uri = params["textDocument"]["uri"]
        pos = Position(
            line=params["position"]["line"],
            character=params["position"]["character"],
        )
        ast_result = self._get_ast(uri)
        if ast_result is None:
            return None

        # Find the innermost function call at this position
        text = self.doc_manager.get_text(uri)
        if text is None:
            return None

        # Walk backwards from cursor to find the opening paren
        lines = text.split("\n")
        if pos.line >= len(lines):
            return None

        line_text = lines[pos.line]
        # Count parens before cursor
        paren_count = 0
        func_name = None
        for i in range(pos.character - 1, -1, -1):
            if line_text[i] == ")":
                paren_count += 1
            elif line_text[i] == "(":
                if paren_count == 0:
                    # Found the opening paren, now get the function name
                    j = i - 1
                    while j >= 0 and (line_text[j].isalnum() or line_text[j] in "_."):
                        j -= 1
                    func_name = line_text[j + 1:i]
                    break
                paren_count -= 1

        if not func_name:
            return None

        # Look up the function in AST
        sym = ast_result.find_symbol(func_name)
        if sym is None or not sym.params:
            return None

        # Build signature information
        parameters = []
        for param in sym.params:
            parameters.append(ParameterInformation(
                label=param,
            ))

        sig_info = SignatureInformation(
            label=f"{func_name}({', '.join(sym.params)})",
            parameters=parameters,
            documentation=sym.doc,
        )

        return {
            "signatures": [sig_info.to_dict()],
            "activeSignature": 0,
            "activeParameter": 0,
        }

    def _handle_type_inference(self, params: dict) -> dict:
        """Return inferred types for all variables and functions in the document."""
        uri = params["textDocument"]["uri"]
        text = self.doc_manager.get_text(uri)
        if text is None:
            return {"types": [], "errors": [f"Document not found: {uri}"]}
        result = infer_types(text)
        return {
            "types": [{"name": t.name, "type": t.inferred_type, "line": t.line} for t in result.types],
            "errors": result.errors,
        }

    def _handle_complexity_analysis(self, params: dict) -> dict:
        """Return cyclomatic complexity report for the document."""
        uri = params["textDocument"]["uri"]
        text = self.doc_manager.get_text(uri)
        if text is None:
            return {"functions": [], "totalComplexity": 0, "averageComplexity": 0.0, "maxComplexity": 0, "error": f"Document not found: {uri}"}
        report = analyze_complexity(text)
        return {
            "functions": [{"name": f.name, "complexity": f.complexity, "lineStart": f.line_start, "lineEnd": f.line_end, "riskLevel": f.risk_level} for f in report.functions],
            "totalComplexity": report.total_complexity,
            "averageComplexity": report.average_complexity,
            "maxComplexity": report.max_complexity,
            "functionCount": report.function_count,
            "error": report.error,
        }

    # ── Diagnostics ────────────────────────────────────────────────────────

    def _get_diagnostics(self, uri: str) -> list[dict]:
        """Compute diagnostics for a document using AST."""
        text = self.doc_manager.get_text(uri)
        if text is None:
            return []

        ast_result = parse_source(text)
        diags = []

        # Syntax errors from AST
        for error in ast_result.errors:
            diags.append(Diagnostic(
                range=Range(
                    Position(error["line"], error["column"]),
                    Position(error["line"], error["column"] + 1),
                ),
                message=error["message"],
                severity=DiagnosticSeverity.ERROR,
            ).to_dict())

        # Trailing open paren or comma (heuristic)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped.endswith("(") or stripped.endswith(","):
                diags.append(Diagnostic(
                    range=Range(Position(i, len(stripped) - 1), Position(i, len(stripped))),
                    message="Possible syntax error: trailing open parenthesis or comma",
                    severity=DiagnosticSeverity.WARNING,
                ).to_dict())

        return diags

    def _publish_diagnostics(self, uri: str) -> None:
        """Compute diagnostics and publish them to the client."""
        diags = self._get_diagnostics(uri)
        if self._notification_callback:
            self._notification_callback({
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {
                    "uri": uri,
                    "diagnostics": diags,
                },
            })

    # ── Helpers ────────────────────────────────────────────────────────────

    def _error_response(self, msg_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
