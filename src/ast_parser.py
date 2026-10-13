"""AST-based Python source parser for LSP features."""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Any


class SymbolKind:
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    IMPORT = "import"
    METHOD = "method"


@dataclass
class Symbol:
    name: str
    kind: str
    line_start: int
    line_end: int
    col_start: int = 0
    col_end: int = 0
    params: list[str] = field(default_factory=list)
    returns: str | None = None
    type_annotation: str | None = None
    bases: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    doc: str | None = None
    is_async: bool = False
    is_method: bool = False
    parent: str | None = None
    children: list[Symbol] = field(default_factory=list)


@dataclass
class Scope:
    kind: str  # module, function, class
    name: str
    line_start: int
    line_end: int
    locals: list[str] = field(default_factory=list)
    children: list[Scope] = field(default_factory=list)


@dataclass
class ImportInfo:
    name: str
    module: str | None
    imported_name: str | None = None
    is_relative: bool = False
    level: int = 0


@dataclass
class ParseResult:
    symbols: list[Symbol] = field(default_factory=list)
    scopes: list[Scope] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def find_symbol(self, name: str) -> Symbol | None:
        for sym in self.symbols:
            if sym.name == name:
                return sym
        return None

    def get_symbols_at_line(self, line: int) -> list[Symbol]:
        return [s for s in self.symbols if s.line_start <= line <= s.line_end]

    def get_symbols_in_range(self, start: int, end: int) -> list[Symbol]:
        return [s for s in self.symbols if s.line_start >= start and s.line_end <= end]

    def get_names_in_scope(self, line: int) -> list[str]:
        """Get all names visible at a given line."""
        names: list[str] = []
        for scope in self.scopes:
            if scope.line_start <= line <= scope.line_end:
                names.extend(scope.locals)
        # Always include module-level names
        module_scope = next((s for s in self.scopes if s.kind == "module"), None)
        if module_scope:
            names.extend(module_scope.locals)
        return list(set(names))


def _get_annotation_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Subscript):
        value = _get_annotation_str(node.value)
        slice_val = _get_annotation_str(node.slice)
        return f"{value}[{slice_val}]"
    if isinstance(node, ast.Attribute):
        value = _get_annotation_str(node.value)
        return f"{value}.{node.attr}"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _get_annotation_str(node.left)
        right = _get_annotation_str(node.right)
        return f"{left} | {right}"
    if isinstance(node, ast.Tuple):
        elts = [_get_annotation_str(e) for e in node.elts]
        return ", ".join(elts)
    return None


def _get_decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _get_decorator_name(node.func)
    return ""


def _get_docstring(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
    return None


def _extract_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    params: list[str] = []
    for arg in node.args.args:
        params.append(arg.arg)
    for arg in node.args.kwonlyargs:
        params.append(arg.arg)
    if node.args.vararg:
        params.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        params.append(f"**{node.args.kwarg.arg}")
    return params


def _extract_bases(node: ast.ClassDef) -> list[str]:
    bases: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(base.attr)
    return bases


def _extract_symbols_from_body(body: list[ast.stmt], parent_name: str | None = None,
                                is_method: bool = False) -> list[Symbol]:
    symbols: list[Symbol] = []
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sym = Symbol(
                name=stmt.name,
                kind=SymbolKind.FUNCTION,
                line_start=stmt.lineno - 1,
                line_end=(stmt.end_lineno or stmt.lineno) - 1,
                col_start=stmt.col_offset,
                col_end=(stmt.end_col_offset or stmt.col_offset),
                params=_extract_params(stmt),
                returns=_get_annotation_str(stmt.returns),
                decorators=[_get_decorator_name(d) for d in stmt.decorator_list],
                doc=_get_docstring(stmt),
                is_async=isinstance(stmt, ast.AsyncFunctionDef),
                is_method=is_method,
                parent=parent_name,
            )
            # Extract nested symbols
            sym.children = _extract_symbols_from_body(stmt.body, stmt.name, is_method=True)
            symbols.append(sym)
            symbols.extend(sym.children)
        elif isinstance(stmt, ast.ClassDef):
            sym = Symbol(
                name=stmt.name,
                kind=SymbolKind.CLASS,
                line_start=stmt.lineno - 1,
                line_end=(stmt.end_lineno or stmt.lineno) - 1,
                col_start=stmt.col_offset,
                col_end=(stmt.end_col_offset or stmt.col_offset),
                bases=_extract_bases(stmt),
                decorators=[_get_decorator_name(d) for d in stmt.decorator_list],
                doc=_get_docstring(stmt),
                parent=parent_name,
            )
            # Extract methods and class variables
            sym.children = _extract_symbols_from_body(stmt.body, stmt.name, is_method=True)
            symbols.append(sym)
            symbols.extend(sym.children)
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    sym = Symbol(
                        name=target.id,
                        kind=SymbolKind.VARIABLE,
                        line_start=stmt.lineno - 1,
                        line_end=(stmt.end_lineno or stmt.lineno) - 1,
                        col_start=stmt.col_offset,
                        col_end=(stmt.end_col_offset or stmt.col_offset),
                        parent=parent_name,
                    )
                    symbols.append(sym)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            symbols.append(Symbol(
                                name=elt.id,
                                kind=SymbolKind.VARIABLE,
                                line_start=stmt.lineno - 1,
                                line_end=(stmt.end_lineno or stmt.lineno) - 1,
                                col_start=stmt.col_offset,
                                col_end=(stmt.end_col_offset or stmt.col_offset),
                                parent=parent_name,
                            ))
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            symbols.append(Symbol(
                name=stmt.target.id,
                kind=SymbolKind.VARIABLE,
                line_start=stmt.lineno - 1,
                line_end=(stmt.end_lineno or stmt.lineno) - 1,
                col_start=stmt.col_offset,
                col_end=(stmt.end_col_offset or stmt.col_offset),
                type_annotation=_get_annotation_str(stmt.annotation),
                parent=parent_name,
            ))
        elif isinstance(stmt, ast.NamedExpr) and isinstance(stmt.target, ast.Name):
            # Walrus operator := creates a new variable
            symbols.append(Symbol(
                name=stmt.target.id,
                kind=SymbolKind.VARIABLE,
                line_start=stmt.lineno - 1,
                line_end=(stmt.end_lineno or stmt.lineno) - 1,
                col_start=stmt.col_offset,
                col_end=(stmt.end_col_offset or stmt.col_offset),
                parent=parent_name,
            ))
        elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
            # Augmented assignment doesn't create a new symbol
            pass
        elif isinstance(stmt, ast.If):
            # Walrus operator in if test
            for node in ast.walk(stmt.test):
                if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
                    symbols.append(Symbol(
                        name=node.target.id,
                        kind=SymbolKind.VARIABLE,
                        line_start=node.lineno - 1,
                        line_end=(node.end_lineno or node.lineno) - 1,
                        col_start=node.col_offset,
                        col_end=(node.end_col_offset or node.col_offset),
                        parent=parent_name,
                    ))
            symbols.extend(_extract_symbols_from_body(stmt.body, parent_name, is_method))
            symbols.extend(_extract_symbols_from_body(stmt.orelse, parent_name, is_method))
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            if isinstance(stmt.target, ast.Name):
                symbols.append(Symbol(
                    name=stmt.target.id,
                    kind=SymbolKind.VARIABLE,
                    line_start=stmt.lineno - 1,
                    line_end=(stmt.end_lineno or stmt.lineno) - 1,
                    col_start=stmt.col_offset,
                    col_end=(stmt.end_col_offset or stmt.col_offset),
                    parent=parent_name,
                ))
            symbols.extend(_extract_symbols_from_body(stmt.body, parent_name, is_method))
            symbols.extend(_extract_symbols_from_body(stmt.orelse, parent_name, is_method))
        elif isinstance(stmt, ast.While):
            symbols.extend(_extract_symbols_from_body(stmt.body, parent_name, is_method))
            symbols.extend(_extract_symbols_from_body(stmt.orelse, parent_name, is_method))
        elif isinstance(stmt, ast.With):
            symbols.extend(_extract_symbols_from_body(stmt.body, parent_name, is_method))
        elif isinstance(stmt, ast.Try):
            symbols.extend(_extract_symbols_from_body(stmt.body, parent_name, is_method))
            for handler in stmt.handlers:
                symbols.extend(_extract_symbols_from_body(handler.body, parent_name, is_method))
            symbols.extend(_extract_symbols_from_body(stmt.orelse, parent_name, is_method))
            symbols.extend(_extract_symbols_from_body(stmt.finalbody, parent_name, is_method))
        elif isinstance(stmt, ast.Global):
            pass  # Global declarations don't create new symbols
        elif isinstance(stmt, ast.Nonlocal):
            pass  # Nonlocal declarations don't create new symbols
    return symbols


def _extract_scopes(body: list[ast.stmt], parent_kind: str = "module",
                     parent_name: str = "<module>") -> list[Scope]:
    scopes: list[Scope] = []
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_scope = Scope(
                kind="function",
                name=stmt.name,
                line_start=stmt.lineno - 1,
                line_end=(stmt.end_lineno or stmt.lineno) - 1,
                locals=[arg.arg for arg in stmt.args.args],
            )
            # Populate function locals with variable assignments
            for child in stmt.body:
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            func_scope.locals.append(target.id)
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    func_scope.locals.append(child.target.id)
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_scope.locals.append(child.name)
            func_scope.children = _extract_scopes(stmt.body, "function", stmt.name)
            scopes.append(func_scope)
            scopes.extend(func_scope.children)
        elif isinstance(stmt, ast.ClassDef):
            class_scope = Scope(
                kind="class",
                name=stmt.name,
                line_start=stmt.lineno - 1,
                line_end=(stmt.end_lineno or stmt.lineno) - 1,
            )
            # Populate class-level variable assignments and method names
            for child in stmt.body:
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            class_scope.locals.append(target.id)
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    class_scope.locals.append(child.target.id)
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_scope.locals.append(child.name)
            class_scope.children = _extract_scopes(stmt.body, "class", stmt.name)
            scopes.append(class_scope)
            scopes.extend(class_scope.children)
        elif isinstance(stmt, ast.If):
            scopes.extend(_extract_scopes(stmt.body, parent_kind, parent_name))
            scopes.extend(_extract_scopes(stmt.orelse, parent_kind, parent_name))
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            if isinstance(stmt.target, ast.Name):
                # Add loop variable to current scope
                for s in scopes:
                    if s.kind == parent_kind and s.name == parent_name:
                        s.locals.append(stmt.target.id)
                        break
            scopes.extend(_extract_scopes(stmt.body, parent_kind, parent_name))
            scopes.extend(_extract_scopes(stmt.orelse, parent_kind, parent_name))
        elif isinstance(stmt, ast.While):
            scopes.extend(_extract_scopes(stmt.body, parent_kind, parent_name))
            scopes.extend(_extract_scopes(stmt.orelse, parent_kind, parent_name))
        elif isinstance(stmt, ast.With):
            scopes.extend(_extract_scopes(stmt.body, parent_kind, parent_name))
        elif isinstance(stmt, ast.Try):
            scopes.extend(_extract_scopes(stmt.body, parent_kind, parent_name))
            for handler in stmt.handlers:
                scopes.extend(_extract_scopes(handler.body, parent_kind, parent_name))
            scopes.extend(_extract_scopes(stmt.orelse, parent_kind, parent_name))
            scopes.extend(_extract_scopes(stmt.finalbody, parent_kind, parent_name))
    return scopes


def _extract_imports(tree: ast.Module) -> list[ImportInfo]:
    imports: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    name=alias.asname or alias.name,
                    module=alias.name,
                    imported_name=None,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level > 0:
                module = "." * node.level + module
            for alias in node.names:
                imports.append(ImportInfo(
                    name=alias.asname or alias.name,
                    module=module,
                    imported_name=alias.name if alias.asname else None,
                    is_relative=node.level > 0,
                    level=node.level,
                ))
    return imports


def parse_source(source: str) -> ParseResult:
    """Parse Python source code and extract symbols, scopes, and imports."""
    result = ParseResult()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        result.errors.append({
            "message": str(e),
            "line": (e.lineno or 1) - 1,
            "column": e.offset or 0,
            "severity": 1,
        })
        return result
    except Exception as e:
        result.errors.append({
            "message": str(e),
            "line": 0,
            "column": 0,
            "severity": 1,
        })
        return result

    # Module scope
    module_scope = Scope(
        kind="module",
        name="<module>",
        line_start=0,
        line_end=len(source.split("\n")) - 1,
    )

    # Extract symbols
    result.symbols = _extract_symbols_from_body(tree.body)

    # Extract scopes
    result.scopes = _extract_scopes(tree.body)
    result.scopes.insert(0, module_scope)

    # Extract imports
    result.imports = _extract_imports(tree)

    # Populate module scope locals with symbols and imports
    for sym in result.symbols:
        if sym.parent is None:
            module_scope.locals.append(sym.name)
    for imp in result.imports:
        module_scope.locals.append(imp.name)

    return result
