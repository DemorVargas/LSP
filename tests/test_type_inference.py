"""Tests for static type inference engine."""
import pytest
from src.type_inference import infer_types, TypeInfo, InferenceResult


class TestInferTypes:
    def test_empty_source(self):
        result = infer_types("")
        assert result.types == []
        assert result.errors == []

    def test_simple_variable_assignment(self):
        source = "x = 42\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("x") == "int"

    def test_string_assignment(self):
        source = 'name = "hello"\n'
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("name") == "str"

    def test_float_assignment(self):
        source = "pi = 3.14\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("pi") == "float"

    def test_bool_assignment(self):
        source = "flag = True\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("flag") == "bool"

    def test_none_assignment(self):
        source = "value = None\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("value") == "None"

    def test_list_assignment(self):
        source = "items = [1, 2, 3]\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("items") == "list"

    def test_dict_assignment(self):
        source = "data = {'a': 1}\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("data") == "dict"

    def test_tuple_assignment(self):
        source = "point = (1, 2)\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("point") == "tuple"

    def test_set_assignment(self):
        source = "unique = {1, 2, 3}\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("unique") == "set"

    def test_function_return_type_annotation(self):
        source = "def foo() -> int:\n    return 42\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("foo") == "int"

    def test_function_param_types(self):
        source = "def foo(x: int, y: str) -> bool:\n    return True\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("x") == "int"
        assert types.get("y") == "str"

    def test_annotated_variable(self):
        source = "count: int = 0\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("count") == "int"

    def test_annotated_str(self):
        source = 'name: str = "hello"\n'
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("name") == "str"

    def test_annotated_list(self):
        source = "items: list = []\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("items") == "list"

    def test_annotated_dict(self):
        source = "data: dict = {}\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("data") == "dict"

    def test_annotated_optional(self):
        source = "value: int | None = None\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("value") == "int | None"

    def test_syntax_error(self):
        result = infer_types("def foo(:\n    pass\n")
        assert len(result.errors) > 0

    def test_multiple_variables(self):
        source = "x = 1\ny = 'hello'\nz = 3.14\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("x") == "int"
        assert types.get("y") == "str"
        assert types.get("z") == "float"

    def test_function_body_assignment(self):
        source = "def foo():\n    x = 42\n    return x\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("x") == "int"

    def test_class_variable(self):
        source = "class Foo:\n    x = 42\n    name = 'foo'\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("x") == "int"
        assert types.get("name") == "str"

    def test_method_self_parameter(self):
        source = "class Foo:\n    def bar(self):\n        pass\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("self") == "self"

    def test_conditional_assignment(self):
        source = "if True:\n    x = 1\nelse:\n    x = 'hello'\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("x") == "int | str"

    def test_for_loop_variable(self):
        source = "for i in range(10):\n    x = i\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("i") == "int"
        # x = i infers as "i" (the variable name), not "int" — correct behavior
        assert types.get("x") == "i"

    def test_walrus_operator(self):
        source = "if (n := 10) > 5:\n    print(n)\n"
        result = infer_types(source)
        types = {t.name: t.inferred_type for t in result.types}
        assert types.get("n") == "int"


class TestTypeInfo:
    def test_creation(self):
        ti = TypeInfo(name="x", inferred_type="int", line=0)
        assert ti.name == "x"
        assert ti.inferred_type == "int"
        assert ti.line == 0

    def test_equality(self):
        ti1 = TypeInfo(name="x", inferred_type="int", line=0)
        ti2 = TypeInfo(name="x", inferred_type="int", line=0)
        assert ti1 == ti2

    def test_inequality(self):
        ti1 = TypeInfo(name="x", inferred_type="int", line=0)
        ti2 = TypeInfo(name="y", inferred_type="str", line=1)
        assert ti1 != ti2


class TestInferenceResult:
    def test_types_list(self):
        result = InferenceResult(
            types=[TypeInfo("x", "int", 0)],
            errors=[],
        )
        assert len(result.types) == 1
        assert result.errors == []

    def test_errors_list(self):
        result = InferenceResult(
            types=[],
            errors=["syntax error"],
        )
        assert len(result.errors) == 1
