"""Cyclomatic complexity analysis engine."""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionComplexity:
    name: str
    complexity: int
    line_start: int
    line_end: int
    risk_level: str = "low"

    def __post_init__(self):
        if self.complexity <= 5:
            self.risk_level = "low"
        elif self.complexity <= 10:
            self.risk_level = "medium"
        elif self.complexity <= 20:
            self.risk_level = "high"
        else:
            self.risk_level = "critical"


@dataclass
class ComplexityReport:
    functions: list[FunctionComplexity] = field(default_factory=list)
    error: str | None = None

    @property
    def total_complexity(self) -> int:
        return sum(f.complexity for f in self.functions)

    @property
    def average_complexity(self) -> float:
        if not self.functions:
            return 0.0
        return self.total_complexity / len(self.functions)

    @property
    def max_complexity(self) -> int:
        if not self.functions:
            return 0
        return max(f.complexity for f in self.functions)

    @property
    def function_count(self) -> int:
        return len(self.functions)

    def risk_level(self, name: str) -> str:
        for f in self.functions:
            if f.name == name:
                return f.risk_level
        return "unknown"


def _compute_complexity(node: ast.AST) -> int:
    """Compute cyclomatic complexity for a function/method AST node."""
    complexity = 1  # Base complexity

    for child in ast.walk(node):
        if isinstance(child, ast.If):
            complexity += 1
        elif isinstance(child, ast.For):
            complexity += 1
        elif isinstance(child, ast.AsyncFor):
            complexity += 1
        elif isinstance(child, ast.While):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.With):
            complexity += 1
        elif isinstance(child, ast.AsyncWith):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += 1
        elif isinstance(child, ast.comprehension):
            if child.ifs:
                complexity += len(child.ifs)
        elif isinstance(child, ast.IfExp):
            complexity += 1

    # Handle match statements (Python 3.10+)
    for child in ast.walk(node):
        if isinstance(child, ast.Match):
            complexity += len(child.cases)

    return complexity


def analyze_complexity(source: str) -> ComplexityReport:
    """Analyze cyclomatic complexity for all functions in source code."""
    report = ComplexityReport()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        report.error = str(e)
        return report
    except Exception as e:
        report.error = str(e)
        return report

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_complexity = _compute_complexity(node)
            fc = FunctionComplexity(
                name=node.name,
                complexity=func_complexity,
                line_start=node.lineno - 1,
                line_end=(node.end_lineno or node.lineno) - 1,
            )
            report.functions.append(fc)

    return report
