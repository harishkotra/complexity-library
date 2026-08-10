from __future__ import annotations

import ast
import hashlib
import math
from dataclasses import dataclass, field
from typing import Protocol

from app.domain import (
    AlgorithmPattern,
    ComplexityAnalysis,
    ComplexitySignature,
    SpaceComplexity,
    SupportedLanguage,
    TimeComplexity,
)


@dataclass
class Facts:
    loop_depth: int = 0
    has_loop: bool = False
    has_halving_loop: bool = False
    has_sort: bool = False
    has_binary_search: bool = False
    has_two_pointer_scan: bool = False
    recursive_calls: int = 0
    allocations: int = 0
    unknown_calls: list[str] = field(default_factory=list)
    operations: list[str] = field(default_factory=list)
    branches: int = 0
    early_returns: int = 0
    breaks: int = 0
    continues: int = 0
    source_facts: list["SourceFact"] = field(default_factory=list)


@dataclass(frozen=True)
class SourceFact:
    kind: str
    line: int
    column: int


@dataclass(frozen=True)
class ComplexityIR:
    function_name: str
    facts: Facts


@dataclass(frozen=True)
class ParsedProgram:
    language: SupportedLanguage
    tree: ast.Module
    function: ast.FunctionDef | ast.AsyncFunctionDef


class LanguageAnalyzer(Protocol):
    """Contract each supported language adapter must satisfy."""

    language: SupportedLanguage

    def parse(self, code: str) -> ParsedProgram: ...
    def normalize(self, parsed: ParsedProgram) -> str: ...
    def fingerprint(self, parsed: ParsedProgram) -> str: ...
    def build_ir(self, parsed: ParsedProgram) -> ComplexityIR: ...
    def analyze(self, parsed: ParsedProgram) -> ComplexityAnalysis: ...


class FingerprintNormalizer(ast.NodeTransformer):
    """Erase local naming noise while retaining syntax and known built-in calls."""

    _builtins = {"append", "add", "enumerate", "get", "len", "max", "min", "print", "range", "sort", "sorted"}

    def __init__(self) -> None:
        self.names: dict[str, str] = {}

    def _normal_name(self, value: str) -> str:
        if value in self._builtins:
            return value
        if value not in self.names:
            self.names[value] = f"v{len(self.names)}"
        return self.names[value]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = "function"
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = self._normal_name(node.arg)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = self._normal_name(node.id)
        return node


class PythonLanguageAnalyzer:
    language = SupportedLanguage.PYTHON

    def parse(self, code: str) -> ParsedProgram:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise ValueError(f"Python could not parse this code: {exc.msg} (line {exc.lineno}).") from exc
        functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not functions:
            raise ValueError("Add a top-level Python function so the analyzer has a clear entry point.")
        return ParsedProgram(language=self.language, tree=tree, function=functions[0])

    def normalize(self, parsed: ParsedProgram) -> str:
        normalized = FingerprintNormalizer().visit(ast.parse(ast.unparse(parsed.function)))
        ast.fix_missing_locations(normalized)
        return ast.dump(normalized, annotate_fields=True, include_attributes=False)

    def fingerprint(self, parsed: ParsedProgram) -> str:
        return hashlib.sha256(self.normalize(parsed).encode("utf-8")).hexdigest()

    def build_ir(self, parsed: ParsedProgram) -> ComplexityIR:
        function = parsed.function
        visitor = PythonFactsVisitor(function.name)
        for statement in function.body:
            visitor.visit(statement)
        return ComplexityIR(function_name=function.name, facts=visitor.facts)

    def analyze(self, parsed: ParsedProgram) -> ComplexityAnalysis:
        return _analysis_from_facts(self.build_ir(parsed).facts)


class PythonFactsVisitor(ast.NodeVisitor):
    def __init__(self, function_name: str) -> None:
        self.facts = Facts()
        self._depth = 0
        self._function_name = function_name

    def visit_For(self, node: ast.For) -> None:
        self._depth += 1
        self.facts.has_loop = True
        self.facts.loop_depth = max(self.facts.loop_depth, self._depth)
        self.facts.operations.append("iteration")
        self.facts.source_facts.append(SourceFact("for_loop", node.lineno, node.col_offset))
        self.generic_visit(node)
        self._depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._depth += 1
        self.facts.has_loop = True
        self.facts.loop_depth = max(self.facts.loop_depth, self._depth)
        self.facts.operations.append("iteration")
        self.facts.source_facts.append(SourceFact("while_loop", node.lineno, node.col_offset))
        if self._contains_halving_assignment(node):
            self.facts.has_halving_loop = True
        if self._looks_like_binary_search(node):
            self.facts.has_binary_search = True
        if self._looks_like_two_pointer_scan(node):
            self.facts.has_two_pointer_scan = True
        self.generic_visit(node)
        self._depth -= 1

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self.facts.allocations += 1
        self.facts.has_loop = True
        self.facts.loop_depth = max(self.facts.loop_depth, len(node.generators))
        self.facts.operations.extend(["iteration", "allocation"])
        self.facts.source_facts.append(SourceFact("comprehension", node.lineno, node.col_offset))
        self.generic_visit(node)

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp

    def visit_List(self, node: ast.List) -> None:
        self.facts.allocations += 1
        self.facts.source_facts.append(SourceFact("allocation", node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.facts.branches += 1
        self.facts.source_facts.append(SourceFact("branch", node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.facts.early_returns += 1
        self.facts.source_facts.append(SourceFact("return", node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_Break(self, node: ast.Break) -> None:
        self.facts.breaks += 1
        self.facts.source_facts.append(SourceFact("break", node.lineno, node.col_offset))

    def visit_Continue(self, node: ast.Continue) -> None:
        self.facts.continues += 1
        self.facts.source_facts.append(SourceFact("continue", node.lineno, node.col_offset))

    def visit_Call(self, node: ast.Call) -> None:
        name = self._call_name(node.func)
        if name == self._function_name:
            self.facts.recursive_calls += 1
        elif name in {"sorted", "sort"}:
            self.facts.has_sort = True
            self.facts.operations.append("sort")
        elif name in {"append", "add", "get", "len", "range", "enumerate", "min", "max", "print"}:
            self.facts.operations.append(name)
        elif name:
            self.facts.unknown_calls.append(name)
        self.generic_visit(node)

    @staticmethod
    def _call_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @staticmethod
    def _contains_halving_assignment(node: ast.While) -> bool:
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign) and isinstance(child.op, (ast.FloorDiv, ast.Div)):
                if isinstance(child.value, ast.Constant) and child.value.value == 2:
                    return True
            if isinstance(child, ast.Assign) and isinstance(child.value, ast.BinOp):
                if isinstance(child.value.op, (ast.FloorDiv, ast.Div)) and isinstance(child.value.right, ast.Constant) and child.value.right.value == 2:
                    return True
        return False

    @staticmethod
    def _looks_like_binary_search(node: ast.While) -> bool:
        """Recognize the conventional low/high/mid loop without executing it."""
        has_midpoint = False
        updated_bound_names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Assign) and isinstance(child.value, ast.BinOp) and isinstance(child.value.op, (ast.FloorDiv, ast.Div)):
                if isinstance(child.value.right, ast.Constant) and child.value.right.value == 2:
                    has_midpoint = True
            if isinstance(child, (ast.Assign, ast.AugAssign)):
                targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id.lower() in {"low", "left", "lo", "high", "right", "hi"}:
                        updated_bound_names.add(target.id.lower())
        return has_midpoint and len(updated_bound_names) >= 2

    @staticmethod
    def _looks_like_two_pointer_scan(node: ast.While) -> bool:
        names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign) and isinstance(child.target, ast.Name) and isinstance(child.op, (ast.Add, ast.Sub)):
                if child.target.id.lower() in {"left", "right", "start", "end", "i", "j"}:
                    names.add(child.target.id.lower())
        return len(names) >= 2


def _analysis_from_facts(facts: Facts) -> ComplexityAnalysis:

    if facts.recursive_calls >= 2:
        time, pattern, confidence, reason = (
            TimeComplexity.EXPONENTIAL,
            AlgorithmPattern.RECURSION,
            0.78,
            "The function branches into multiple calls to itself, so its call tree grows exponentially.",
        )
    elif facts.recursive_calls == 1 and facts.has_sort:
        time, pattern, confidence, reason = (
            TimeComplexity.N_LOG_N,
            AlgorithmPattern.DIVIDE_AND_CONQUER,
            0.83,
            "The function recurses while sorting/merging work is present; this matches divide-and-conquer growth.",
        )
    elif facts.has_sort:
        time, pattern, confidence, reason = (
            TimeComplexity.N_LOG_N,
            AlgorithmPattern.DIVIDE_AND_CONQUER,
            0.92,
            "A sorting operation dominates the function and is assumed to take O(n log n).",
        )
    elif facts.has_binary_search:
        time, pattern, confidence, reason = (
            TimeComplexity.LOGARITHMIC,
            AlgorithmPattern.LOGARITHMIC_HALVING,
            0.96,
            "The low/high bounds converge through a midpoint, which is the binary-search halving pattern.",
        )
    elif facts.has_halving_loop:
        time, pattern, confidence, reason = (
            TimeComplexity.LOGARITHMIC,
            AlgorithmPattern.LOGARITHMIC_HALVING,
            0.93,
            "The loop repeatedly halves its working value, leaving about log₂(n) iterations.",
        )
    elif facts.loop_depth >= 3:
        time, pattern, confidence, reason = (
            TimeComplexity.CUBIC,
            AlgorithmPattern.NESTED_LOOP,
            0.95,
            "Three nested input-dependent loops combine into cubic work.",
        )
    elif facts.loop_depth >= 2:
        time, pattern, confidence, reason = (
            TimeComplexity.QUADRATIC,
            AlgorithmPattern.NESTED_LOOP,
            0.94,
            "Nested iteration visits a pair of positions for each input element, producing quadratic work.",
        )
    elif facts.loop_depth == 1 or facts.recursive_calls == 1:
        time, pattern, confidence, reason = (
            TimeComplexity.LINEAR,
            AlgorithmPattern.LINEAR_SCAN if facts.loop_depth else AlgorithmPattern.RECURSION,
            0.90,
            "The function visits one element or recursion level at a time, so work grows with the input.",
        )
    else:
        time, pattern, confidence, reason = (
            TimeComplexity.CONSTANT,
            AlgorithmPattern.CONSTANT,
            0.97,
            "No input-dependent loop or recursion was found in the selected function.",
        )

    limitations: list[str] = []
    if facts.unknown_calls:
        confidence = min(confidence, 0.72)
        limitations.append(f"The cost of {', '.join(sorted(set(facts.unknown_calls)))}() could not be determined locally.")
    assumptions = ["Built-in sort operations are treated as O(n log n)."] if facts.has_sort else []
    space = SpaceComplexity.LINEAR if facts.allocations else (SpaceComplexity.LOGARITHMIC if facts.recursive_calls else SpaceComplexity.CONSTANT)
    return ComplexityAnalysis(
        time_complexity=time,
        space_complexity=space,
        confidence=confidence,
        pattern=pattern,
        reasoning=reason,
        dominant_operations=list(dict.fromkeys(facts.operations + (["binary search"] if facts.has_binary_search else []) + (["two pointer movement"] if facts.has_two_pointer_scan else []))) or ["constant work"],
        assumptions=assumptions,
        limitations=limitations,
        signature=ComplexitySignature(
            recursion=bool(facts.recursive_calls),
            loop_depth=facts.loop_depth,
            input_types=["collection"],
            operations=list(dict.fromkeys(facts.operations)),
            language=SupportedLanguage.PYTHON,
        ),
    )


_python_analyzer = PythonLanguageAnalyzer()


def analyze_python(code: str) -> ComplexityAnalysis:
    return _python_analyzer.analyze(_python_analyzer.parse(code))


def normalize_python(code: str) -> str:
    return _python_analyzer.normalize(_python_analyzer.parse(code))


def fingerprint_python(code: str) -> str:
    return _python_analyzer.fingerprint(_python_analyzer.parse(code))


def build_python_ir(code: str) -> ComplexityIR:
    return _python_analyzer.build_ir(_python_analyzer.parse(code))


def unsupported_analysis(language: SupportedLanguage) -> ComplexityAnalysis:
    return ComplexityAnalysis(
        time_complexity=TimeComplexity.UNKNOWN,
        space_complexity=SpaceComplexity.UNKNOWN,
        confidence=0.0,
        pattern=AlgorithmPattern.UNKNOWN,
        reasoning=f"{language.value.title()} analysis is planned but not enabled in this first deterministic slice.",
        limitations=["Choose Python for a working deterministic analysis."],
        signature=ComplexitySignature(loop_depth=0, language=language),
    )
