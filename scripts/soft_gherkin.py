#!/usr/bin/env python3
"""Soft Gherkin mutation testing for Chronograph.

Mutates one string literal or number per Given/When/Then step in
features/**/*.feature, reruns the acceptance runner, and reports mutants
that survive (i.e. the runner still passes even though the spec text
was changed). Surviving mutants indicate under-asserting step defs or
vacuous scenarios.

Robust against interruption:
- Original bytes are saved to a `.orig` sibling before any mutation.
- Every mutation writes atomically via a temp file + os.replace().
- On SIGINT / SIGTERM / normal exit, the atexit handler restores from `.orig`.
- If a `.orig` file already exists at startup, its contents are treated as
  the true original (recovery from a prior interrupted run).
"""
from __future__ import annotations

import atexit
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FEATURES = REPO / "features"
RUNNER = REPO / "tests" / "acceptance_runner.py"

_ORIGINALS: dict[Path, str] = {}


def _atomic_write(path: Path, text: str) -> None:
    """Write text to path via temp-file + rename so an interrupt can't leave a half-written file."""
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _register_original(path: Path) -> str:
    """Record the pristine content of path, using an existing `.orig` if a prior run left one."""
    orig_marker = path.with_suffix(path.suffix + ".orig")
    if orig_marker.exists():
        original = orig_marker.read_text()
        _atomic_write(path, original)
    else:
        original = path.read_text()
        _atomic_write(orig_marker, original)
    _ORIGINALS[path] = original
    return original


def _restore_all() -> None:
    for path, original in _ORIGINALS.items():
        try:
            _atomic_write(path, original)
        except FileNotFoundError:
            continue
        marker = path.with_suffix(path.suffix + ".orig")
        try:
            marker.unlink()
        except FileNotFoundError:
            pass


def _install_signal_restorers() -> None:
    def _handler(signum, _frame):
        _restore_all()
        raise SystemExit(128 + signum)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            pass


def mutate_line(line: str) -> str | None:
    stripped = line.strip()
    if not re.match(r"^(Given|When|And|Then) ", stripped):
        return None

    string_match = re.search(r'"([^"]+)"', line)
    if string_match:
        original = string_match.group(1)
        mutated = original + "_MUTANT"
        return line.replace(f'"{original}"', f'"{mutated}"', 1)

    number_match = re.search(r"\b(\d+)\b", line)
    if number_match:
        original = number_match.group(1)
        mutated = str(int(original) + 1)
        return line.replace(original, mutated, 1)

    return None


def run_acceptance() -> bool:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def main() -> int:
    _install_signal_restorers()
    atexit.register(_restore_all)

    surviving: list[tuple[str, int, str, str]] = []

    for feature_path in sorted(FEATURES.glob("*.feature")):
        original_text = _register_original(feature_path)
        original_lines = original_text.splitlines()
        for idx, line in enumerate(original_lines):
            mutated_line = mutate_line(line)
            if mutated_line is None or mutated_line == line:
                continue
            mutated_lines = list(original_lines)
            mutated_lines[idx] = mutated_line
            _atomic_write(feature_path, "\n".join(mutated_lines) + "\n")
            try:
                still_passes = run_acceptance()
            finally:
                _atomic_write(feature_path, original_text)
            if still_passes:
                surviving.append((feature_path.name, idx + 1, line.strip(), mutated_line.strip()))

    if not surviving:
        print("OK: no surviving Gherkin mutants")
        return 0
    for name, lineno, original, mutated in surviving:
        print(f"SURVIVING MUTANT: {name}:{lineno}")
        print(f"  original: {original}")
        print(f"  mutated:  {mutated}", file=sys.stderr)
    print(f"\nFAIL: {len(surviving)} surviving mutant(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
