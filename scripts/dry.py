#!/usr/bin/env python3
"""Stdlib duplicate-block detector for Chronograph.

Detects near-duplicate multi-line blocks in src/chronograph using hashed
sliding windows of tokenized source lines. Non-code lines (blank, comments,
docstrings, imports) are ignored.

Threshold: fails if any duplicated block spans MIN_BLOCK_LINES or more
non-trivial lines and appears in two or more distinct locations.
"""

from __future__ import annotations

import hashlib
import sys
import tokenize
from collections import defaultdict
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "chronograph"
MIN_BLOCK_LINES = 6


def normalize_line(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""
    if stripped.startswith(("import ", "from ")):
        return ""
    return stripped


def collect_lines(path: Path) -> list[tuple[int, str]]:
    docstring_lines: set[int] = set()
    try:
        with path.open("rb") as fh:
            for tok in tokenize.tokenize(fh.readline):
                if tok.type == tokenize.STRING and tok.start[1] == 0:
                    for lineno in range(tok.start[0], tok.end[0] + 1):
                        docstring_lines.add(lineno)
    except tokenize.TokenError:
        pass
    lines: list[tuple[int, str]] = []
    for idx, raw in enumerate(path.read_text().splitlines(), start=1):
        if idx in docstring_lines:
            continue
        normalized = normalize_line(raw)
        if normalized:
            lines.append((idx, normalized))
    return lines


def hash_window(window: list[str]) -> str:
    joined = "\n".join(window)
    return hashlib.sha256(joined.encode()).hexdigest()


def main() -> int:
    windows: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for path in sorted(PACKAGE_ROOT.glob("*.py")):
        rows = collect_lines(path)
        for i in range(len(rows) - MIN_BLOCK_LINES + 1):
            window = [row[1] for row in rows[i : i + MIN_BLOCK_LINES]]
            first_lineno = rows[i][0]
            windows[hash_window(window)].append((path.name, first_lineno))

    duplicates = [
        (digest, locations) for digest, locations in windows.items() if len(locations) > 1
    ]
    if not duplicates:
        print("OK: no near-duplicate blocks found")
        return 0

    for _, locations in duplicates:
        locs = ", ".join(f"{name}:{lineno}" for name, lineno in locations)
        print(f"DUPLICATE ({MIN_BLOCK_LINES}+ line block): {locs}", file=sys.stderr)
    print(f"\nFAIL: {len(duplicates)} duplicated block(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
