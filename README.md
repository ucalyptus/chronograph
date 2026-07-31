# Chronograph

Chronograph is a local-first work-continuity engine: it ingests fragmented work signals, extracts commitments, builds a source-grounded context graph, persists everything locally, and exposes curated work state through a Python API, CLI, and HTTP JSON API.

It is designed around the product thesis from `docs/product-notes.md`: useful proactive AI needs continuity, provenance, task curation, and explicit review surfaces — not another reactive prompt box.

## What is built

Chronograph now includes the full local product surface, not a scaffold:

- **Deterministic extractor** for commitments, owners, deadlines, blockers, review/risk signals, projects, artifacts, decisions, and completion updates.
- **Context graph engine** that merges fragmented signals into durable work items and indexes relationships such as `owns`, `due`, `blocked_by`, `part_of`, `produces`, `needs_review`, and `sourced_from`.
- **Source-grounded provenance** with source IDs, source types, exact quotes, and chronicle/audit events.
- **Lifecycle tracking** for `active`, `blocked`, `needs_review`, `done`, and `stale` work.
- **Curated review queue** for blocked, risky, ambiguous, or explicit review-needed work.
- **SQLite persistence** for local/private storage.
- **JSON import/export** for complete workspace backup and restore.
- **Search** across source text and work item state.
- **CLI** for ingest/list/active/review/show/search/export/import/serve.
- **Stdlib HTTP API** for local integrations.
- **Executable Gherkin acceptance tests** plus unit/integration tests.

## Repository layout

- `docs/requirements.md` — software requirements specification
- `docs/product-notes.md` — original product/requirements notes
- `docs/traceability.md` — mapping from characteristics to scenarios/tests/code
- `AGENTS.md` — repo conventions for AI/human contributors
- `features/chronograph_context.feature` — Gherkin acceptance scenarios
- `src/chronograph/models.py` — source, work item, relationship, and event models
- `src/chronograph/extractor.py` — deterministic extraction rules
- `src/chronograph/engine.py` — graph/work-continuity engine
- `src/chronograph/store.py` — SQLite persistence
- `src/chronograph/cli.py` — command line interface
- `src/chronograph/api.py` — stdlib WSGI JSON API
- `tests/acceptance_runner.py` — dependency-free Gherkin runner
- `tests/test_chronograph.py` — compatibility/domain tests
- `tests/test_extractor_units.py` — pure-helper unit tests for extractor + models + engine helpers
- `tests/test_property.py` — stdlib-random property tests (deterministic seeds)
- `tests/test_full_system.py` — extractor, engine, storage, CLI, and API integration tests
- `tests/test_e2e.py` — real-socket API tests + `chronograph serve` subprocess flow + CLI subcommand E2E
- `scripts/crap.py` — CRAP score reporter (needs `coverage/coverage.json`)
- `scripts/boundary.py` — intra-package dep-direction enforcement
- `scripts/dry.py` — near-duplicate-block detector
- `scripts/soft_gherkin.py` — mutates `.feature` literals to catch under-asserting step defs
- `Makefile` — canonical quality-gate targets
- `.pre-commit-config.yaml` — local hook runner for the fast gates

## Run locally

From the repo root:

```bash
PYTHONPATH=src python3 tests/acceptance_runner.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall src tests
```

Or use the `Makefile` for the full quality-gate sweep:

```bash
make test        # unit + integration + property + e2e via unittest discover
make acceptance  # Gherkin scenarios (custom stdlib runner)
make compile     # compileall
make all         # everything above plus boundary, dry, coverage, crap
```

Expected result:

- 13 Gherkin acceptance scenarios pass
- 96 unit / integration / property / e2e tests pass
- compileall succeeds
- boundary and DRY scripts report no violations

## Development dependencies

Runtime is stdlib-only (see `NFR-02` in `docs/requirements.md`). Dev-only tooling (coverage, mutmut) lives under `[project.optional-dependencies].dev` in `pyproject.toml`:

```bash
pip install -e ".[dev]"
make coverage        # coverage.py → coverage/coverage.json
make crap            # CRAP-score report (uses coverage/coverage.json)
make mutation        # mutmut against extractor + models
make gherkin_mutation  # soft Gherkin mutation scan
```

See `AGENTS.md` for repo-wide conventions and the mapping to the swarmforge 11-gate taxonomy.

## Python API

```python
from chronograph import Chronograph, ChronographStore

graph = Chronograph(ChronographStore("chronograph.db"))
graph.ingest("m1", "meeting", "Finance should follow up with the customer")
graph.ingest("s1", "slack", "Need this by Friday")
graph.ingest("e1", "email", "Alex owns the finance follow-up now")

item = graph.active_work_items()[0]
assert item.title == "Finance follow-up"
assert item.owner == "Alex"
assert item.deadline == "Friday"
assert graph.relationship_exists("Alex", "owns", "Finance follow-up")
```

## CLI

```bash
PYTHONPATH=src python3 -m chronograph.cli --db chronograph.db ingest \
  --id m1 --type meeting \
  --text "Sam will send customer follow-up by Friday"

PYTHONPATH=src python3 -m chronograph.cli --db chronograph.db review
PYTHONPATH=src python3 -m chronograph.cli --db chronograph.db show "Sam"
PYTHONPATH=src python3 -m chronograph.cli --db chronograph.db export > backup.json
```

## HTTP API

Start the local API:

```bash
PYTHONPATH=src python3 -m chronograph.cli --db chronograph.db serve --host 127.0.0.1 --port 8765
```

Endpoints:

- `GET /health`
- `POST /sources`
- `GET /work-items`
- `GET /active`
- `GET /review`
- `GET /search?q=<query>`
- `GET /graph/<entity>`
- `GET /export`

## Status

Working local-first implementation. Private GitHub remote: `ucalyptus/chronograph`.
