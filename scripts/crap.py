#!/usr/bin/env python3
"""Stdlib-only CRAP-score reporter for Chronograph.

CRAP(f) = cx^2 * (1 - cov)^3 + cx
where cx is a cyclomatic-complexity heuristic and cov is per-function coverage.

Reads coverage/coverage.json produced by:
    coverage run --source=src/chronograph -m unittest discover -s tests
    coverage json -o coverage/coverage.json

Exits non-zero when any function's CRAP exceeds THRESHOLD.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

THRESHOLD = 30
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "chronograph"
COVERAGE_JSON = Path(__file__).resolve().parents[1] / "coverage" / "coverage.json"


def cyclomatic(node: ast.AST) -> int:
    """Approximate cyclomatic complexity of a function body."""
    score = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Try, ast.Match),
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(len(child.values) - 1, 0)
        elif isinstance(child, ast.IfExp):
            score += 1
        elif isinstance(child, ast.comprehension):
            score += 1 + len(child.ifs)
    return score


def load_coverage(path: Path) -> dict[str, set[int]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {
        str(Path(rel).resolve()): set(info.get("executed_lines", []))
        for rel, info in data.get("files", {}).items()
    }


def function_coverage(executed: set[int], start: int, end: int) -> float:
    total = max(end - start + 1, 1)
    if not executed:
        return 0.0
    covered = sum(1 for line in range(start, end + 1) if line in executed)
    return covered / total


def crap(cx: int, cov: float) -> float:
    return (cx * cx) * ((1 - cov) ** 3) + cx


def main() -> int:
    coverage = load_coverage(COVERAGE_JSON)
    if not coverage:
        print(f"warning: no coverage found at {COVERAGE_JSON}; treating everything as uncovered", file=sys.stderr)

    rows = []
    for src in sorted(SOURCE_ROOT.glob("*.py")):
        tree = ast.parse(src.read_text(), filename=str(src))
        executed = coverage.get(str(src.resolve()), set())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cx = cyclomatic(node)
                start = node.lineno
                end = getattr(node, "end_lineno", node.lineno)
                cov = function_coverage(executed, start, end)
                score = crap(cx, cov)
                rows.append((score, cx, cov, f"{src.name}:{start}:{node.name}"))

    rows.sort(reverse=True)
    print(f"{'CRAP':>7}  {'CX':>3}  {'COV':>5}  FUNCTION")
    for score, cx, cov, label in rows:
        print(f"{score:7.2f}  {cx:3d}  {cov:5.2f}  {label}")

    worst = rows[0][0] if rows else 0.0
    if worst > THRESHOLD:
        print(f"\nFAIL: worst CRAP {worst:.2f} > threshold {THRESHOLD}", file=sys.stderr)
        return 1
    print(f"\nOK: worst CRAP {worst:.2f} <= threshold {THRESHOLD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
