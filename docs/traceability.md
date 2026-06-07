# Chronograph traceability

This document maps the original Chronograph characteristics into executable behavior.

## CH-01 Context graph

- **Characteristic:** Connect people, projects, decisions, tasks, deadlines, owners, meetings, documents, messages, and artifacts.
- **Gherkin:** `Scenario: Merge fragmented signals into one active work item`
- **Acceptance check:** `tests/acceptance_runner.py` verifies one active item merges meeting + Slack + email sources.
- **Unit test:** `test_merges_fragments_by_topic_into_one_active_work_item`
- **Code:** `Chronograph.ingest`, `WorkItem.add_source`, `_extract_title`, `_merge_item_fields`

## CH-02 Task extraction and curation

- **Characteristic:** Separate real commitments from conversational noise, active work, stale work, blockers, review-needed items, and low-value clutter.
- **Gherkin:** `Scenario: Curate real commitments instead of dumping conversational noise`
- **Acceptance check:** extracts `Board memo` but ignores speculative logo redesign chatter.
- **Unit test:** `test_curates_real_commitments_and_ignores_speculative_noise`
- **Code:** `_extract_work_items`, `_is_noise`, `_extract_title`, `_extract_owner`, `_extract_deadline`

## CH-03 Source grounding and provenance

- **Characteristic:** Every extracted item should point back to source material and preserve provenance.
- **Gherkin:** `Scenario: Keep source grounding for extracted work`
- **Acceptance check:** verifies source quote and source ID are retained.
- **Unit test:** `test_keeps_source_quotes_and_provenance`
- **Code:** `Source`, `WorkItem.source_ids`, `WorkItem.source_quotes`, `WorkItem.provenance`

## CH-04 Continuity over time

- **Characteristic:** Track what changed, open loops, owners, blockers, and review state over time.
- **Gherkin:** `Scenario: Track continuity as signals change over time`
- **Acceptance check:** later Slack signal marks investor response as blocked on finance numbers.
- **Unit test:** `test_tracks_blocked_state_and_recent_changes`
- **Code:** `_extract_blocker`, `_merge_item_fields`, `recent_changes`

## CH-05 Proactive surfacing

- **Characteristic:** Surface what needs attention without forcing the user to reconstruct state or process notification spam.
- **Gherkin:** `Scenario: Surface proactive review items without notification spam`
- **Acceptance check:** exactly one review item is surfaced with a clear reason.
- **Unit test:** `test_surfaces_review_items_with_reason`
- **Code:** `_extract_review_reason`, `review_items`

## CH-06 Sandbox-local state

- **Characteristic:** A Chronograph workspace should maintain local/private state rather than global shared memory.
- **Gherkin:** Covered by `Given an empty Chronograph workspace` in every scenario.
- **Acceptance check:** every scenario constructs a fresh `AcceptanceWorld` and `Chronograph`.
- **Unit test:** `test_sandbox_local_instances_do_not_share_state`
- **Code:** `Chronograph.__init__`

## Verification commands

```bash
python3 tests/acceptance_runner.py
PYTHONPATH=src python3 -m unittest tests.test_chronograph -v
python3 -m compileall src tests
```
