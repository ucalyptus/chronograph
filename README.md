# Chronograph

Private repository scaffold for Chronograph.

Chronograph is a small, local-first MVP of a context graph and task extraction layer. It turns fragmented work signals into structured, source-grounded work state.

## What is implemented

The current implementation covers the product characteristics from `docs/product-notes.md`:

- **Context graph:** source fragments are merged into one active work item by topic.
- **Task extraction:** real commitments are extracted from meeting/doc/chat/email text while obvious speculative noise is ignored.
- **Source grounding:** work items retain source IDs, source types, and exact source quotes.
- **Continuity:** later signals can update owner, deadline, blocked state, blocker, and recent changes.
- **Proactive surfacing:** risky/review-needed work is exposed through `review_items()`.
- **Sandbox-local state:** each `Chronograph()` instance owns isolated in-memory state.

## Repository layout

- `features/chronograph_context.feature` — Gherkin acceptance scenarios
- `tests/acceptance_runner.py` — dependency-free Gherkin runner for the feature grammar
- `tests/test_chronograph.py` — unit tests for the domain API
- `src/chronograph/__init__.py` — MVP implementation
- `docs/product-notes.md` — original product/requirements notes
- `docs/traceability.md` — mapping from characteristic to Gherkin, acceptance test, unit test, and code

## Run locally

From the repo root:

```bash
python3 tests/acceptance_runner.py
PYTHONPATH=src python3 -m unittest tests.test_chronograph -v
python3 -m compileall src tests
```

Expected result:

- all 5 Gherkin acceptance scenarios pass
- all 6 unit tests pass
- compileall succeeds

## Minimal API

```python
from chronograph import Chronograph

graph = Chronograph()
graph.ingest("m1", "meeting", "Finance should follow up with the customer")
graph.ingest("s1", "slack", "Need this by Friday")
graph.ingest("e1", "email", "Alex owns the finance follow-up now")

item = graph.active_work_items()[0]
assert item.title == "Finance follow-up"
assert item.owner == "Alex"
assert item.deadline == "Friday"
```

## Status

Local repository is working and verified. Remote GitHub private repo is pending credentials.
