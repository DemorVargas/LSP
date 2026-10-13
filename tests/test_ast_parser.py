"""Tests for the AST parser — the foundation for all advanced features."""
import pytest
from src.ast_parser import parse_source, SymbolKind


class TestParseSource:
    def test_empty_source(self):
        result = parse_source("")
        assert result.symbols == []
        assert result.errors == []

    def test_simple_function(self):
        source = "def hello():\n    pass\n"
        result = parse_source(source)
        assert len(result.symbols) == 1
        sym = result.symbols[0]
        assert sym.name == "hello"
        assert sym.kind == SymbolKind.FUNCTION
        assert sym.line_start == 0

    def test_function_with_params(self):
        source = "def greet(name, greeting='hello'):\n    pass\n"
        result = parse_source(source)
        sym = result.symbols[0]
        assert sym.name == "greet"
        assert "name" in sym.params
        assert "greeting" in sym.params

    def test_function_with_return_annotation(self):
        source = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = parse_source(source)
        sym = result.symbols[0]
        assert sym.returns == "int"

    def test_class(self):
        source = "class MyClass:\n    pass\n"
        result = parse_source(source)
        assert len(result.symbols) == 1
        assert result.symbols[0].name == "MyClass"
        assert result.symbols[0].kind == SymbolKind.CLASS

    def test_class_with_methods(self):
        source = "class Foo:\n    def bar(self):\n        pass\n\n    def baz(self, x):\n        return x\n"
        result = parse_source(source)
        names = [s.name for s in result.symbols]
        assert "Foo" in names
        assert "bar" in names
        assert "baz" in names

    def test_class_inheritance(self):
        source = "class Child(Base, Mixin):\n    pass\n"
        result = parse_source(source)
        sym = result.symbols[0]
        assert sym.name == "Child"
        assert "Base" in sym.bases
        assert "Mixin" in sym.bases

    def test_async_function(self):
        source = "async def fetch():\n    pass\n"
        result = parse_source(source)
        sym = result.symbols[0]
        assert sym.name == "fetch"
        assert sym.is_async is True

    def test_decorated_function(self):
        source = "@decorator\ndef my_func():\n    pass\n"
        result = parse_source(source)
        sym = result.symbols[0]
        assert "decorator" in sym.decorators

    def test_variable_assignment(self):
        source = "x = 42\n"
        result = parse_source(source)
        assert len(result.symbols) == 1
        assert result.symbols[0].name == "x"
        assert result.symbols[0].kind == SymbolKind.VARIABLE

    def test_type_annotated_variable(self):
        source = "count: int = 0\n"
        result = parse_source(source)
        assert result.symbols[0].name == "count"
        assert result.symbols[0].type_annotation == "int"

    def test_import(self):
        source = "import os\n"
        result = parse_source(source)
        assert len(result.imports) == 1
        assert result.imports[0].name == "os"
        assert result.imports[0].module == "os"

    def test_from_import(self):
        source = "from os.path import join\n"
        result = parse_source(source)
        assert len(result.imports) == 1
        assert result.imports[0].name == "join"
        assert result.imports[0].module == "os.path"

    def test_from_import_alias(self):
        source = "from collections import OrderedDict as OD\n"
        result = parse_source(source)
        assert result.imports[0].name == "OD"
        assert result.imports[0].imported_name == "OrderedDict"

    def test_syntax_error(self):
        source = "def foo(:\n    pass\n"
        result = parse_source(source)
        assert len(result.errors) > 0
        assert result.errors[0]["message"]

    def test_syntax_error_line_number(self):
        source = "x = 1\ny = 2\ndef foo(:\n    pass\n"
        result = parse_source(source)
        assert result.errors[0]["line"] == 2

    def test_docstring_extraction(self):
        source = 'def hello():\n    """Say hello."""\n    pass\n'
        result = parse_source(source)
        assert result.symbols[0].doc == "Say hello."

    def test_class_docstring(self):
        source = 'class Foo:\n    """A foo."""\n    pass\n'
        result = parse_source(source)
        assert result.symbols[0].doc == "A foo."

    def test_nested_function(self):
        source = "def outer():\n    def inner():\n        pass\n    return inner\n"
        result = parse_source(source)
        names = [s.name for s in result.symbols]
        assert "outer" in names
        assert "inner" in names

    def test_method_is_async(self):
        source = "class Foo:\n    async def bar(self):\n        pass\n"
        result = parse_source(source)
        bar = [s for s in result.symbols if s.name == "bar"][0]
        assert bar.is_async is True

    def test_class_variable(self):
        source = "class Foo:\n    x = 42\n    y = 'hello'\n"
        result = parse_source(source)
        var_names = [s.name for s in result.symbols if s.kind == SymbolKind.VARIABLE]
        assert "x" in var_names
        assert "y" in var_names

    def test_global_variable_scope(self):
        source = "x = 1\ndef foo():\n    y = 2\n"
        result = parse_source(source)
        scopes = result.scopes
        assert any(s.kind == "module" for s in scopes)
        assert any(s.kind == "function" for s in scopes)

    def test_lambda_not_extracted(self):
        source = "f = lambda x: x + 1\n"
        result = parse_source(source)
        assert result.symbols[0].name == "f"
        assert result.symbols[0].kind == SymbolKind.VARIABLE

    def test_property_decorator(self):
        source = "class Foo:\n    @property\n    def bar(self):\n        return 1\n"
        result = parse_source(source)
        bar = [s for s in result.symbols if s.name == "bar"][0]
        assert "property" in bar.decorators

    def test_staticmethod_decorator(self):
        source = "class Foo:\n    @staticmethod\n    def bar():\n        pass\n"
        result = parse_source(source)
        bar = [s for s in result.symbols if s.name == "bar"][0]
        assert "staticmethod" in bar.decorators

    def test_classmethod_decorator(self):
        source = "class Foo:\n    @classmethod\n    def bar(cls):\n        pass\n"
        result = parse_source(source)
        bar = [s for s in result.symbols if s.name == "bar"][0]
        assert "classmethod" in bar.decorators

    def test_walrus_operator(self):
        source = "if (n := 10) > 5:\n    print(n)\n"
        result = parse_source(source)
        assert any(s.name == "n" for s in result.symbols)

    def test_fstring(self):
        source = 'name = "world"\nmsg = f"hello {name}"\n'
        result = parse_source(source)
        assert len(result.symbols) == 2
        assert result.symbols[0].name == "name"
        assert result.symbols[1].name == "msg"

    def test_type_alias(self):
        source = "from typing import List\nVector = List[float]\n"
        result = parse_source(source)
        assert result.symbols[0].name == "Vector"

    def test_global_statement(self):
        source = "x = 0\ndef foo():\n    global x\n    x = 1\n"
        result = parse_source(source)
        assert any(s.name == "x" for s in result.symbols)

    def test_nonlocal_statement(self):
        source = "def outer():\n    x = 0\n    def inner():\n        nonlocal x\n        x = 1\n"
        result = parse_source(source)
        assert any(s.name == "x" for s in result.symbols)

    def test_star_import(self):
        source = "from os import *\n"
        result = parse_source(source)
        assert len(result.imports) == 1
        assert result.imports[0].name == "*"

    def test_relative_import(self):
        source = "from .sibling import helper\n"
        result = parse_source(source)
        assert result.imports[0].name == "helper"
        assert result.imports[0].module == ".sibling"

    def test_multiple_assignments(self):
        source = "x = y = 0\n"
        result = parse_source(source)
        names = [s.name for s in result.symbols]
        assert "x" in names
        assert "y" in names

    def test_augmented_assignment_not_new_symbol(self):
        source = "x = 0\nx += 1\n"
        result = parse_source(source)
        x_syms = [s for s in result.symbols if s.name == "x"]
        assert len(x_syms) == 1


class TestSymbolLookup:
    def test_find_symbol_by_name(self):
        source = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        result = parse_source(source)
        foo = result.find_symbol("foo")
        assert foo is not None
        assert foo.name == "foo"

    def test_find_symbol_returns_none_if_missing(self):
        result = parse_source("x = 1\n")
        assert result.find_symbol("nonexistent") is None

    def test_find_symbol_in_class(self):
        source = "class Foo:\n    def bar(self):\n        pass\n"
        result = parse_source(source)
        bar = result.find_symbol("bar")
        assert bar is not None
        assert bar.kind == SymbolKind.FUNCTION

    def test_get_symbols_at_line(self):
        source = "def foo():\n    x = 1\n    y = 2\n"
        result = parse_source(source)
        symbols = result.get_symbols_at_line(1)
        assert any(s.name == "x" for s in symbols)

    def test_get_symbols_in_range(self):
        source = "def foo():\n    x = 1\n    y = 2\n\ndef bar():\n    pass\n"
        result = parse_source(source)
        symbols = result.get_symbols_in_range(0, 3)
        names = [s.name for s in symbols]
        assert "foo" in names
        assert "x" in names
        assert "bar" not in names


class TestScopeAnalysis:
    def test_module_scope(self):
        result = parse_source("x = 1\n")
        assert any(s.kind == "module" for s in result.scopes)

    def test_function_scope(self):
        result = parse_source("def foo():\n    pass\n")
        assert any(s.kind == "function" for s in result.scopes)

    def test_class_scope(self):
        result = parse_source("class Foo:\n    pass\n")
        assert any(s.kind == "class" for s in result.scopes)

    def test_scope_contains_line(self):
        result = parse_source("def foo():\n    x = 1\n    y = 2\n")
        func_scope = [s for s in result.scopes if s.kind == "function"][0]
        assert func_scope.line_start <= 1 <= func_scope.line_end
        assert func_scope.line_start <= 2 <= func_scope.line_end

    def test_scope_children(self):
        result = parse_source("def foo():\n    x = 1\n    y = 2\n")
        func_scope = [s for s in result.scopes if s.kind == "function"][0]
        assert "x" in func_scope.locals
        assert "y" in func_scope.locals


class TestCompletionContext:
    def test_get_names_in_scope_module(self):
        source = "import os\nx = 1\n\ndef foo():\n    y = 2\n"
        result = parse_source(source)
        names = result.get_names_in_scope(line=0)
        assert "os" in names
        assert "x" in names
        assert "foo" in names

    def test_get_names_in_scope_function(self):
        source = "import os\nx = 1\n\ndef foo():\n    y = 2\n    z = 3\n"
        result = parse_source(source)
        names = result.get_names_in_scope(line=3)
        assert "os" in names
        assert "x" in names
        assert "y" in names
        assert "z" in names

    def test_get_names_in_scope_class(self):
        source = "class Foo:\n    x = 1\n    def bar(self):\n        pass\n"
        result = parse_source(source)
        names = result.get_names_in_scope(line=2)
        assert "Foo" in names
        assert "x" in names
        assert "bar" in names
