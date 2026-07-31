# Chronograph — Agent conventions

Every agent editing this repository (Claude Code, Copilot CLI, Codex, aider, Cursor, ...) must follow these repo-wide rules. They are the encoded lessons from the SDLC audit and are enforced by hooks and CI where possible.

## Zero-dep runtime — non-negotiable

`pyproject.toml` declares `dependencies = []`. Chronograph runtime must work with the Python standard library only (NFR-02 in `docs/requirements.md`). Any new runtime dependency requires an ADR justifying it.

Dev-only tooling (coverage, mutmut, etc.) goes into `[project.optional-dependencies].dev`. Never move a dev tool into runtime deps.

## Quality gates (swarmforge 11-gate taxonomy + lint/format)

Every change must keep the local quality-gate sweep green:

```bash
make all
```

Individual targets:

| Target             | What it enforces                                                |
| ------------------ | --------------------------------------------------------------- |
| `make lint`        | `ruff check src tests scripts` — style + likely-bug rules       |
| `make format`      | `ruff format --check src tests scripts` — canonical formatting  |
| `make test`        | `unittest` discover: unit + integration + property + e2e suites |
| `make acceptance`  | Custom-runner Gherkin scenarios (`features/`)                   |
| `make compile`     | `compileall` on `src/` and `tests/`                             |
| `make coverage`    | `coverage.py`, JSON dump into `coverage/coverage.json`          |
| `make crap`        | `scripts/crap.py` — CRAP score ≤ 30 per function                |
| `make boundary`    | `scripts/boundary.py` — declared dep-direction only             |
| `make dry`         | `scripts/dry.py` — no 6+ line duplicate blocks in `src/`        |
| `make mutation`    | `mutmut` against `extractor` and `models`                       |
| `make gherkin_mutation` | Soft mutation of `.feature` string/number literals         |

## Pre-commit hooks

The repo ships a `.pre-commit-config.yaml` with local hooks for ruff (lint + format), `compileall`, `unittest`, the acceptance runner, boundary, and DRY. Install once after cloning:

```bash
pip install -e ".[dev]"
make precommit   # or:   pre-commit install
```

After install, every `git commit` runs these hooks against the staged files; the commit is rejected if any hook fails. Bypass only with `git commit --no-verify` and only for emergencies.

## Test runner

Use stdlib `unittest`, not `pytest`. The acceptance runner is deliberately dependency-free (`tests/acceptance_runner.py`). Do not port to `behave`.

## Layered dependency direction (enforced by `scripts/boundary.py`)

```
models    <-  store
models    <-  extractor
models,store,extractor  <-  engine
engine,store  <-  api
engine,store,api  <-  cli
```

Never import "up the stack": `models.py` imports nothing from this package, and `store.py`/`extractor.py` import only from `models`.

## Adding tests

- Unit tests for a new pure helper go in `tests/test_extractor_units.py` (extractor / models pure helpers) or `tests/test_chronograph.py` (higher-level unit tests).
- Integration tests exercising `Chronograph` + real `ChronographStore` go in `tests/test_full_system.py`.
- Property tests (stdlib random with `random.seed(0)` — no `hypothesis`) go in `tests/test_property.py`.
- Real-socket E2E tests go in `tests/test_e2e.py`.
- Gherkin scenarios go in `features/chronograph_context.feature`; register step definitions in `tests/acceptance_runner.py`.

## Adding runtime code

- Prefer stdlib modules. If you need e.g. YAML or HTTP client — use `json` + `wsgiref` + `urllib` first.
- Keep `models.py` free of intra-package imports.
- Do not construct `Source(...)` twice to fetch a default field — call `models.utc_now()` directly.
- The canonical day-of-week list lives at `chronograph.extractor.DAY_WORDS`. Do not duplicate it.

## Style, formatting, and static analysis

- Code style: run `ruff format` and `ruff check`; both must be clean (`make lint` and `make format`).
- Ruff config lives in `[tool.ruff]` in `pyproject.toml`; line length 100, target `py311`, ruleset `E/W/F/I/UP/B/SIM/C4/PIE/RUF`.
- Do not manually reformat around ruff — configure the rule if a rule is genuinely wrong for this codebase.

## Commits

- Trailer `Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>` on Copilot-assisted commits.
- Run `make all` locally before committing.

## Foreign agents / concurrent editors

Other harnesses (Codex CLI, Claude Code sessions, herdr) may write to this repo. If you find uncommitted diffs you did not make, **do not revert**; report and keep to your lane.
