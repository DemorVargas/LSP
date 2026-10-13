"""Tests for cyclomatic complexity analysis."""
import pytest
from src.complexity import analyze_complexity, ComplexityReport, FunctionComplexity


class TestAnalyzeComplexity:
    def test_simple_function_score_1(self):
        source = "def foo():\n    pass\n"
        report = analyze_complexity(source)
        assert len(report.functions) == 1
        assert report.functions[0].name == "foo"
        assert report.functions[0].complexity == 1

    def test_if_statement_adds_1(self):
        source = "def foo(x):\n    if x > 0:\n        return 1\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_multiple_ifs(self):
        source = "def foo(x, y):\n    if x > 0:\n        return 1\n    if y > 0:\n        return 2\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 3

    def test_for_loop_adds_1(self):
        source = "def foo(items):\n    for x in items:\n        print(x)\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_while_loop_adds_1(self):
        source = "def foo(x):\n    while x > 0:\n        x -= 1\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_elif_adds_1(self):
        source = "def foo(x):\n    if x > 0:\n        return 1\n    elif x < 0:\n        return -1\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 3

    def test_else_does_not_add(self):
        source = "def foo(x):\n    if x > 0:\n        return 1\n    return 0\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_try_except_adds_1(self):
        source = "def foo():\n    try:\n        x = 1\n    except ValueError:\n        pass\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_multiple_except_handlers(self):
        source = "def foo():\n    try:\n        x = 1\n    except ValueError:\n        pass\n    except TypeError:\n        pass\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 3

    def test_with_statement_adds_1(self):
        source = "def foo():\n    with open('f') as f:\n        pass\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_boolean_operator_and_adds_1(self):
        source = "def foo(x, y):\n    if x > 0 and y > 0:\n        return 1\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 3

    def test_boolean_operator_or_adds_1(self):
        source = "def foo(x, y):\n    if x > 0 or y > 0:\n        return 1\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 3

    def test_multiple_boolean_operators(self):
        source = "def foo(a, b, c):\n    if a and b or c:\n        return 1\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 4

    def test_nested_function_separate_entry(self):
        source = "def outer(x):\n    def inner(y):\n        if y > 0:\n            return 1\n        return 0\n    return inner(x)\n"
        report = analyze_complexity(source)
        names = [f.name for f in report.functions]
        assert "outer" in names
        assert "inner" in names
        # inner: 1 + if = 2
        inner = [f for f in report.functions if f.name == "inner"][0]
        assert inner.complexity == 2

    def test_class_method_tracked(self):
        source = "class Foo:\n    def bar(self, x):\n        if x > 0:\n            return 1\n        return 0\n"
        report = analyze_complexity(source)
        bar = [f for f in report.functions if f.name == "bar"]
        assert len(bar) == 1
        assert bar[0].complexity == 2

    def test_empty_file(self):
        report = analyze_complexity("")
        assert report.functions == []
        assert report.total_complexity == 0
        assert report.average_complexity == 0.0

    def test_syntax_error_returns_report_with_error(self):
        report = analyze_complexity("def foo(:\n    pass\n")
        assert report.functions == []
        assert report.error is not None

    def test_async_function(self):
        source = "async def fetch(url):\n    if url:\n        return True\n    return False\n"
        report = analyze_complexity(source)
        assert len(report.functions) == 1
        assert report.functions[0].name == "fetch"
        assert report.functions[0].complexity == 2

    def test_list_comprehension_adds_1(self):
        source = "def foo(items):\n    return [x for x in items if x > 0]\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_ternary_adds_1(self):
        source = "def foo(x):\n    return 1 if x > 0 else 0\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 2

    def test_match_case_adds_per_case(self):
        source = "def foo(x):\n    match x:\n        case 1:\n            return 1\n        case 2:\n            return 2\n        case _:\n            return 0\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 4  # base 1 + 3 cases


class TestComplexityReport:
    def test_total_complexity(self):
        source = "def a():\n    pass\ndef b():\n    pass\n"
        report = analyze_complexity(source)
        assert report.total_complexity == 2

    def test_average_complexity(self):
        source = "def a():\n    pass\ndef b(x):\n    if x:\n        pass\n"
        report = analyze_complexity(source)
        assert report.average_complexity == 1.5

    def test_max_complexity(self):
        source = "def a():\n    pass\ndef b(x):\n    if x:\n        pass\n"
        report = analyze_complexity(source)
        assert report.max_complexity == 2

    def test_function_count(self):
        source = "def a():\n    pass\ndef b():\n    pass\ndef c():\n    pass\n"
        report = analyze_complexity(source)
        assert report.function_count == 3

    def test_risk_level_low(self):
        source = "def foo():\n    pass\n"
        report = analyze_complexity(source)
        assert report.risk_level("foo") == "low"

    def test_risk_level_medium(self):
        # 5 ifs + base = 6 complexity = medium
        source = "def foo(x):\n    if x == 1:\n        return 1\n    if x == 2:\n        return 2\n    if x == 3:\n        return 3\n    if x == 4:\n        return 4\n    if x == 5:\n        return 5\n    return 0\n"
        report = analyze_complexity(source)
        assert report.risk_level("foo") == "medium"

    def test_risk_level_high(self):
        # 15 ifs -> complexity 16
        lines = ["def foo(x):"]
        for i in range(15):
            lines.append(f"    if x == {i}:")
            lines.append(f"        return {i}")
        lines.append("    return -1")
        report = analyze_complexity("\n".join(lines))
        assert report.risk_level("foo") == "high"

    def test_risk_level_critical(self):
        # 30 ifs -> complexity 31
        lines = ["def foo(x):"]
        for i in range(30):
            lines.append(f"    if x == {i}:")
            lines.append(f"        return {i}")
        lines.append("    return -1")
        report = analyze_complexity("\n".join(lines))
        assert report.risk_level("foo") == "critical"

    def test_risk_level_unknown_function(self):
        report = analyze_complexity("def foo():\n    pass\n")
        assert report.risk_level("nonexistent") == "unknown"


class TestFunctionComplexity:
    def test_attributes(self):
        fc = FunctionComplexity(
            name="foo",
            complexity=8,
            line_start=0,
            line_end=3,
        )
        assert fc.name == "foo"
        assert fc.complexity == 8
        assert fc.risk_level == "medium"

    def test_risk_level_thresholds(self):
        # 1-5: low
        assert FunctionComplexity("a", 1, 0, 0).risk_level == "low"
        assert FunctionComplexity("b", 5, 0, 0).risk_level == "low"
        # 6-10: medium
        assert FunctionComplexity("c", 6, 0, 0).risk_level == "medium"
        assert FunctionComplexity("d", 10, 0, 0).risk_level == "medium"
        # 11-20: high
        assert FunctionComplexity("e", 11, 0, 0).risk_level == "high"
        assert FunctionComplexity("f", 20, 0, 0).risk_level == "high"
        # 21+: critical
        assert FunctionComplexity("g", 21, 0, 0).risk_level == "critical"


class TestComplexityIntegration:
    def test_realistic_function(self):
        source = """
def process_data(data, mode='default'):
    results = []
    for item in data:
        if item is None:
            continue
        if mode == 'strict':
            if item > 10:
                results.append(item)
            elif item > 5:
                results.append(item * 2)
        elif mode == 'lenient':
            results.append(item)
        else:
            if item > 0:
                results.append(item)
            else:
                results.append(0)
    return results
"""
        report = analyze_complexity(source)
        func = report.functions[0]
        assert func.name == "process_data"
        assert func.complexity >= 5  # Should be reasonably complex
        assert func.risk_level in ("medium", "high")

    def test_class_with_multiple_methods(self):
        source = """
class DataProcessor:
    def __init__(self):
        self.data = []

    def add(self, item):
        if item is not None:
            self.data.append(item)

    def process(self):
        results = []
        for item in self.data:
            if item > 0:
                results.append(item)
        return results
"""
        report = analyze_complexity(source)
        names = [f.name for f in report.functions]
        assert "__init__" in names
        assert "add" in names
        assert "process" in names
        # process has for + if = complexity 3
        process = [f for f in report.functions if f.name == "process"][0]
        assert process.complexity == 3

    def test_decorator_preserved(self):
        source = """
@decorator
def foo(x):
    if x > 0:
        return 1
    return 0
"""
        report = analyze_complexity(source)
        assert len(report.functions) == 1
        assert report.functions[0].complexity == 2

    def test_empty_function_body(self):
        source = "def foo():\n    ...\n"
        report = analyze_complexity(source)
        assert report.functions[0].complexity == 1
