#!/usr/bin/env python3
"""Stdlib boundary/dep-direction check for Chronograph.

Enforces the declared layered dependency graph on `src/chronograph/`.
Fails if any module imports something outside its allow-list.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ALLOWED = {
    "__init__": {"engine", "models", "store"},
    "models": set(),
    "store": {"models"},
    "extractor": {"models"},
    "engine": {"extractor", "models", "store"},
    "api": {"engine", "store"},
    "cli": {"api", "engine", "store"},
}

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "chronograph"


def intra_package_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def main() -> int:
    violations: list[str] = []
    for src in sorted(PACKAGE_ROOT.glob("*.py")):
        module = src.stem
        allowed = ALLOWED.get(module)
        if allowed is None:
            violations.append(f"{src}: unknown module '{module}' — add to ALLOWED map in scripts/boundary.py")
            continue
        for dep in intra_package_imports(src):
            if dep == module:
                continue
            if dep not in allowed:
                violations.append(
                    f"{src}: illegal intra-package import of '.{dep}' (allowed: {sorted(allowed) or '<none>'})"
                )
    for line in violations:
        print(line, file=sys.stderr)
    if violations:
        print(f"\nFAIL: {len(violations)} boundary violation(s)", file=sys.stderr)
        return 1
    print("OK: no boundary violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
