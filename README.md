# MiniLSP — A Language Server Protocol Implementation in Python

A from-scratch LSP server for Python, built with zero third-party dependencies. Parses code with the `ast` module, serves completions/hover/definition/symbols over stdio, and includes static analysis features like type inference and cyclomatic complexity scoring.

## Quick Start

```bash
python3 -m src.main
```

The server speaks LSP over stdio. Pipe JSON-RPC messages in, get responses out.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Client (editor)                                    │
│  sends LSP requests/notifications over stdio        │
└──────────────────────┬──────────────────────────────┘
                       │ Content-Length framed JSON-RPC
┌──────────────────────▼──────────────────────────────┐
│  stdio_server.py  — async reader/writer             │
│  framing.py       — encode/decode JSON-RPC messages │
├─────────────────────────────────────────────────────┤
│  server.py        — request dispatch, lifecycle     │
│  document_manager.py — in-memory document state     │
│  ast_parser.py    — Python ast → symbols, scopes    │
│  lru_cache.py     — cached AST results              │
│  logger.py        — structured JSON logging         │
│  config.py        — file + env configuration        │
├─────────────────────────────────────────────────────┤
│  Feature handlers                                    │
│  type_inference.py  — static type analysis           │
│  complexity.py      — cyclomatic complexity scoring  │
│  types.py           — LSP protocol dataclasses       │
└─────────────────────────────────────────────────────┘
```

## Features

### LSP Standard Features

| Feature | Method | Description |
|---------|--------|-------------|
| Hover | `textDocument/hover` | Shows function signature, class definition, or variable type + docstring |
| Go to Definition | `textDocument/definition` | Resolves symbol name to its definition line via AST |
| Completion | `textDocument/completion` | Scope-aware names + Python builtins + keywords, deduplicated |
| Document Symbols | `textDocument/documentSymbol` | Top-level symbols with nested children (class → methods) |
| Signature Help | `textDocument/signatureHelp` | Parameter info when cursor is inside a function call |
| Diagnostics | `textDocument/publishDiagnostics` | AST syntax errors (ERROR) + trailing paren/comma (WARNING) |

### Custom Analysis Features

| Feature | Method | Description |
|---------|--------|-------------|
| Type Inference | `textDocument/typeInference` | Infers types from annotations, literals, branch merging, loop variables |
| Complexity Analysis | `textDocument/complexityAnalysis` | Cyclomatic complexity per function with risk levels (low/medium/high/critical) |

### Supported Python Syntax

- Functions (sync/async), classes, methods, nested functions
- Type annotations (including `int | None` union syntax)
- Decorators (`@property`, `@staticmethod`, `@classmethod`)
- Walrus operator (`:=`)
- Match/case statements
- Comprehensions (list/dict/set)
- Import styles: `import x`, `from x import y`, `from x import y as z`, `from x import *`, relative imports
- Docstrings

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MINILSP_LOG_LEVEL` | `info` | Logging level: `debug`, `info`, `warning`, `error`, `critical` |
| `MINILSP_LOG_FORMAT` | `json` | Log output format |
| `MINILSP_LOG_OUTPUT` | `stderr` | Log output destination |
| `MINILSP_CACHE_SIZE` | `128` | LRU cache capacity for AST results |
| `MINILSP_MAX_CONCURRENT` | `4` | Maximum concurrent operations |

### Config File

Create a `config.json`:

```json
{
  "logging": {
    "level": "debug",
    "format": "json",
    "output": "stderr"
  },
  "performance": {
    "cache_size": 256,
    "max_concurrent": 8
  }
}
```

## API Examples

### Initialize

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "processId": null,
    "rootUri": "file:///project",
    "capabilities": {}
  }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "capabilities": {
      "textDocumentSync": { "openClose": true, "change": 2 },
      "hoverProvider": true,
      "definitionProvider": true,
      "completionProvider": { "triggerCharacters": [".", "("] },
      "documentSymbolProvider": true,
      "signatureHelpProvider": { "triggerCharacters": ["(", ","] },
      "typeInferenceProvider": true,
      "complexityAnalysisProvider": true
    },
    "serverInfo": { "name": "minilsp", "version": "0.2.0" }
  }
}
```

### Hover

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "textDocument/hover",
  "params": {
    "textDocument": { "uri": "file:///test.py" },
    "position": { "line": 4, "character": 7 }
  }
}
```

### Completion

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "textDocument/completion",
  "params": {
    "textDocument": { "uri": "file:///test.py" },
    "position": { "line": 0, "character": 5 }
  }
}
```

### Type Inference

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "textDocument/typeInference",
  "params": { "textDocument": { "uri": "file:///test.py" } }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "types": [
      { "name": "greet", "type": "int", "line": 0 },
      { "name": "x", "type": "int", "line": 1 },
      { "name": "items", "type": "list", "line": 2 }
    ],
    "errors": []
  }
}
```

### Complexity Analysis

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "textDocument/complexityAnalysis",
  "params": { "textDocument": { "uri": "file:///test.py" } }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "functions": [
      { "name": "process", "complexity": 5, "lineStart": 3, "lineEnd": 12, "riskLevel": "low" },
      { "name": "validate", "complexity": 8, "lineStart": 14, "lineEnd": 20, "riskLevel": "medium" }
    ],
    "totalComplexity": 13,
    "averageComplexity": 6.5,
    "maxComplexity": 8,
    "functionCount": 2,
    "error": null
  }
}
```

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific module tests
python3 -m pytest tests/test_ast_parser.py -v
python3 -m pytest tests/test_complexity.py -v

# Run with coverage
python3 -m pytest tests/ --tb=short
```

**262 tests** across 11 test files, all passing.

## Module Overview

| Module | Purpose | Lines |
|--------|---------|-------|
| `src/framing.py` | JSON-RPC Content-Length encode/decode | 91 |
| `src/types.py` | LSP protocol dataclasses (Position, Range, Diagnostic, etc.) | 209 |
| `src/document_manager.py` | In-memory document state tracking | 91 |
| `src/ast_parser.py` | Python ast → symbols, scopes, imports | 370 |
| `src/lru_cache.py` | LRU cache with capacity + size-bounded eviction | 130 |
| `src/logger.py` | Structured JSON logging with level filtering | 100 |
| `src/config.py` | Config management (file, env vars, dict) | 120 |
| `src/complexity.py` | Cyclomatic complexity analysis engine | 100 |
| `src/type_inference.py` | Static type inference from AST | 205 |
| `src/server.py` | JSON-RPC dispatch, lifecycle, all handlers | 474 |
| `src/stdio_server.py` | Async stdio transport | 99 |
| `src/main.py` | Entry point | 19 |

## Design Decisions

**AST over regex:** All code analysis uses Python's `ast` module. Regex parsing of code is fragile and wrong. AST gives us exact line numbers, scope boundaries, and type information.

**LRU caching:** AST parsing is expensive. Results are cached per-document with an LRU strategy so frequently-accessed documents are always fast.

**Incremental sync:** The server declares `TextDocumentSyncKind.Incremental` and the document manager supports both full and ranged changes, minimizing bandwidth for large files.

**Async stdio:** The transport uses `asyncio.StreamReader` for non-blocking reads, so the server handles large messages without blocking.

**Zero dependencies:** Pure Python stdlib. No `pygls`, no `pylsp`, no third-party packages. Everything is hand-built.

## License

MIT
