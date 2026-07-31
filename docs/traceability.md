# Chronograph traceability

This document maps the Chronograph characteristics into executable behavior.

## CH-01 Context graph

- **Requirement:** FR-04, FR-06
- **Characteristic:** Connect people, projects, decisions, tasks, deadlines, owners, meetings, documents, messages, and artifacts.
- **Gherkin:** `Scenario: Merge fragmented signals into one active work item`; `Scenario: Persist and reload a local workspace`
- **Unit/integration tests:** `test_merges_fragments_tracks_graph_and_chronicle`, `test_sqlite_store_round_trips_state`, `test_graph_neighborhood_returns_all_edges_for_ingested_entity`
- **Code:** `src/chronograph/engine.py`, `src/chronograph/models.py`

## CH-02 Task extraction and curation

- **Requirement:** FR-02, FR-03
- **Characteristic:** Separate real commitments from conversational noise, active work, stale work, blockers, review-needed items, and low-value clutter.
- **Gherkin:** `Scenario: Curate real commitments instead of dumping conversational noise`
- **Unit/integration tests:** `test_extracts_owner_deadline_project_and_artifact`, `test_ignores_speculative_noise`, `tests/test_extractor_units.py` (dedicated helpers), `tests/test_property.py` (extract idempotence, dedupe invariants)
- **Code:** `src/chronograph/extractor.py`

## CH-03 Source grounding and provenance

- **Requirement:** FR-01, FR-05
- **Characteristic:** Every extracted item points back to source material and preserves source IDs, types, quotes, author, metadata, and audit events.
- **Gherkin:** `Scenario: Keep source grounding for extracted work`; `Scenario: Export and import complete state without losing provenance`; `Scenario: Retain source author and metadata for provenance`
- **Unit/integration tests:** `test_keeps_source_quotes_and_provenance`, `test_export_import_preserves_provenance`, `AddSourceAndProvenanceTests`
- **Code:** `Source`, `WorkItem.source_ids`, `WorkItem.source_quotes`, `WorkItem.provenance`, `Chronograph.events`

## CH-04 Continuity over time

- **Requirement:** FR-04, FR-07
- **Characteristic:** Track what changed, open loops, owners, blockers, completion, and review state over time.
- **Gherkin:** `Scenario: Track continuity as signals change over time`; `Scenario: Mark completed work done while retaining source history`
- **Unit/integration tests:** `test_tracks_blocked_state_and_recent_changes`, `test_completion_keeps_history`, `test_contextual_update_applies_when_titleless_signal_follows_one_item`, `MergeFieldsTests`
- **Code:** `Chronograph._resolve_item`, `Chronograph._merge_fields`, `Chronograph._contextual_update`, `Chronograph.recent_changes`

## CH-05 Proactive surfacing

- **Requirement:** FR-08
- **Characteristic:** Surface what needs attention without forcing users to reconstruct state or process notification spam.
- **Gherkin:** `Scenario: Surface proactive review items without notification spam`
- **Unit/integration tests:** `test_review_queue_is_curated`, `test_surfaces_review_items_with_reason`
- **Code:** `Chronograph.review_items`, `Extractor._extract_review_reason`

## CH-06 Sandbox-local persistence

- **Requirement:** FR-09, FR-14
- **Characteristic:** Keep workspace state local/private and reloadable from SQLite.
- **Gherkin:** `Scenario: Persist and reload a local workspace`; `Scenario: Workspace state stays local in the SQLite file`
- **Unit/integration tests:** `test_sqlite_store_round_trips_state`, `test_sandbox_local_instances_do_not_share_state`, `test_search_finds_matches_after_sqlite_reload`
- **Code:** `ChronographStore`, `Chronograph.__init__`

## CH-07 Import/export

- **Requirement:** FR-10
- **Characteristic:** Export and import complete state without losing provenance.
- **Gherkin:** `Scenario: Export and import complete state without losing provenance`
- **Unit/integration tests:** `test_export_import_preserves_provenance`, `test_export_import_round_trip_through_sqlite_file`
- **Code:** `Chronograph.export_json`, `Chronograph.import_json`, `ChronographStore.replace_all`

## CH-08 CLI and API surfaces

- **Requirement:** FR-11, FR-12
- **Characteristic:** Expose local product functionality through a CLI and HTTP JSON API.
- **Gherkin:** `Scenario: The Chronograph CLI exposes the documented commands`; `Scenario: The Chronograph HTTP API responds to the documented endpoints`
- **Unit/integration tests:** `test_cli_ingest_list_review_export`, `test_wsgi_api_ingest_active_review_and_export`, `CliSubcommandE2ETests`, `CliServeSubprocessE2ETests`, `RealSocketApiE2ETests`
- **Code:** `src/chronograph/cli.py`, `src/chronograph/api.py`

## CH-09 Search

- **Requirement:** FR-13
- **Characteristic:** Search source text and work item state.
- **Gherkin:** `Scenario: Search across sources and active work`
- **Unit/integration tests:** `test_search_finds_sources_and_work_items`, `test_search_finds_matches_after_sqlite_reload`
- **Code:** `Chronograph.search`, CLI `search`, API `/search`

## Engineering-quality gates (swarmforge 11-gate taxonomy)

Chronograph's SDLC layer additionally maps to the swarmforge quality-gate taxonomy documented in `~/.agents/skills/swarmforge/SKILL.md` and enforced by `Makefile` + `scripts/` + `.pre-commit-config.yaml`:

| # | Gate | Coverage in this repo |
|---|---|---|
| 1 | Unit | `tests/test_chronograph.py`, `tests/test_extractor_units.py` |
| 2 | Integration | `tests/test_full_system.py` (`ChronographEngineTests`, `PersistenceTests`, `IntegrationAuditTests`) |
| 3 | Property | `tests/test_property.py` (stdlib randomized, deterministic seed) |
| 4 | E2E | `tests/test_e2e.py::RealSocketApiE2ETests`, `CliServeSubprocessE2ETests`, `CliSubcommandE2ETests` |
| 5 | Mutation | `mutmut` config in `pyproject.toml`, runs via `make mutation` |
| 6 | BDD | `features/chronograph_context.feature` + `tests/acceptance_runner.py` |
| 7 | UAT | Same file as BDD — stakeholder-language scenarios are the UAT surface (see `AGENTS.md` for the rationale) |
| 8 | CRAP | `scripts/crap.py` — CRAP = CX² · (1 − cov)³ + CX per function, threshold 30 |
| 9 | DRY | `scripts/dry.py` — stdlib AST duplicate-block detector, min 6 lines |
| 10 | Boundary | `scripts/boundary.py` — enforces declared intra-package dep-direction |
| 11 | Soft Gherkin mutation | `scripts/soft_gherkin.py` — mutates feature literals to catch under-asserting step defs |

## Verification commands

```bash
make all               # everything below in one go
make test              # unit + integration + property + e2e
make acceptance        # Gherkin scenarios
make compile           # compileall
make coverage          # coverage.py (requires dev deps: pip install -e ".[dev]")
make crap              # CRAP report
make boundary          # dep-direction check
make dry               # duplicate-block check
make mutation          # mutmut (requires dev deps)
make gherkin_mutation  # soft Gherkin mutation
```
