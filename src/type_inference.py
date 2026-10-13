"""Static type inference engine using Python's ast module."""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TypeInfo:
    name: str
    inferred_type: str
    line: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypeInfo):
            return NotImplemented
        return self.name == other.name and self.inferred_type == other.inferred_type and self.line == other.line


@dataclass
class InferenceResult:
    types: list[TypeInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _infer_type_from_node(node: ast.AST) -> str | None:
    """Infer type from an AST expression node."""
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        if isinstance(node.value, bool):
            return "bool"
        if isinstance(node.value, int):
            return "int"
        if isinstance(node.value, float):
            return "float"
        if isinstance(node.value, str):
            return "str"
        if isinstance(node.value, bytes):
            return "bytes"
    if isinstance(node, ast.List):
        return "list"
    if isinstance(node, ast.Dict):
        return "dict"
    if isinstance(node, ast.Tuple):
        return "tuple"
    if isinstance(node, ast.Set):
        return "set"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.BinOp):
        left = _infer_type_from_node(node.left)
        right = _infer_type_from_node(node.right)
        if left == right and left is not None:
            return left
        return None
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
    if isinstance(node, ast.BoolOp):
        return None
    if isinstance(node, ast.Compare):
        return "bool"
    if isinstance(node, ast.IfExp):
        body = _infer_type_from_node(node.body)
        orelse = _infer_type_from_node(node.orelse)
        if body == orelse and body is not None:
            return body
        if body and orelse:
            return f"{body} | {orelse}"
        return body or orelse
    return None


def _annotation_to_str(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Subscript):
        value = _annotation_to_str(node.value)
        slice_val = _annotation_to_str(node.slice)
        return f"{value}[{slice_val}]"
    if isinstance(node, ast.Attribute):
        value = _annotation_to_str(node.value)
        return f"{value}.{node.attr}"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = _annotation_to_str(node.left)
        right = _annotation_to_str(node.right)
        return f"{left} | {right}"
    if isinstance(node, ast.Tuple):
        elts = [_annotation_to_str(e) for e in node.elts]
        return ", ".join(elts)
    return None


def infer_types(source: str) -> InferenceResult:
    """Infer types for all variables and functions in source code."""
    result = InferenceResult()
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        result.errors.append(str(e))
        return result
    except Exception as e:
        result.errors.append(str(e))
        return result

    # Merge types for variables assigned in multiple branches (if/else, etc.)
    merged_types: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            ann_type = _annotation_to_str(node.annotation)
            inferred = ann_type or (_infer_type_from_node(node.value) if node.value else None)
            if inferred:
                result.types.append(TypeInfo(
                    name=node.target.id,
                    inferred_type=inferred,
                    line=node.lineno - 1,
                ))
        elif isinstance(node, ast.Assign):
            inferred = _infer_type_from_node(node.value)
            if inferred:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        result.types.append(TypeInfo(
                            name=target.id,
                            inferred_type=inferred,
                            line=node.lineno - 1,
                        ))
                    elif isinstance(target, ast.Tuple):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name):
                                result.types.append(TypeInfo(
                                    name=elt.id,
                                    inferred_type=inferred,
                                    line=node.lineno - 1,
                                ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returns = _annotation_to_str(node.returns)
            if returns:
                result.types.append(TypeInfo(
                    name=node.name,
                    inferred_type=returns,
                    line=node.lineno - 1,
                ))
            # Infer parameter types from annotations, fallback to "self" or "unknown"
            for arg in node.args.args:
                if arg.annotation:
                    ann_type = _annotation_to_str(arg.annotation)
                    if ann_type:
                        result.types.append(TypeInfo(
                            name=arg.arg,
                            inferred_type=ann_type,
                            line=node.lineno - 1,
                        ))
                elif arg.arg == "self":
                    result.types.append(TypeInfo(
                        name=arg.arg,
                        inferred_type="self",
                        line=node.lineno - 1,
                    ))
                else:
                    result.types.append(TypeInfo(
                        name=arg.arg,
                        inferred_type="unknown",
                        line=node.lineno - 1,
                    ))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if isinstance(node.target, ast.Name):
                # Infer loop variable type from iterator
                iter_type = _infer_type_from_node(node.iter)
                if iter_type == "range":
                    loop_type = "int"
                elif iter_type:
                    loop_type = iter_type
                else:
                    loop_type = "unknown"
                result.types.append(TypeInfo(
                    name=node.target.id,
                    inferred_type=loop_type,
                    line=node.lineno - 1,
                ))
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            inferred = _infer_type_from_node(node.value)
            if inferred:
                result.types.append(TypeInfo(
                    name=node.target.id,
                    inferred_type=inferred,
                    line=node.lineno - 1,
                ))
        elif isinstance(node, ast.comprehension):
            if isinstance(node.target, ast.Name):
                result.types.append(TypeInfo(
                    name=node.target.id,
                    inferred_type="unknown",
                    line=node.lineno - 1 if node.lineno else 0,
                ))

    # Post-process: merge types from multiple assignments to the same variable
    type_by_name: dict[str, set[str]] = {}
    for ti in result.types:
        if ti.name not in type_by_name:
            type_by_name[ti.name] = set()
        type_by_name[ti.name].add(ti.inferred_type)

    final_types: list[TypeInfo] = []
    seen_names: set[str] = set()
    for ti in result.types:
        if ti.name in seen_names:
            continue
        seen_names.add(ti.name)
        all_types = type_by_name.get(ti.name, {ti.inferred_type})
        if len(all_types) > 1:
            merged = " | ".join(sorted(all_types - {"unknown"} or all_types))
            final_types.append(TypeInfo(
                name=ti.name,
                inferred_type=merged,
                line=ti.line,
            ))
        else:
            final_types.append(ti)

    result.types = final_types
    return result
