# Chronograph Requirements Specification

## Purpose and scope

Chronograph is a local-first work-continuity engine. It ingests fragmented work signals from meetings, Slack, email, documents, calendars, and task systems; extracts structured commitments; connects them into a context graph; tracks lifecycle changes; and exposes review-ready work state through a Python API, CLI, and HTTP API.

## Non-goals

- It is not an LLM wrapper.
- It does not require cloud services.
- It does not silently discard provenance.
- It does not pretend full autonomy is safe; review-needed work must be surfaced.

## Domain model

- **Source:** Original evidence such as meeting notes, Slack messages, email, document, calendar event, or task-system update.
- **Entity:** Person, project, artifact, topic, deadline, decision, source, or work item.
- **Relationship:** Directed edge connecting entities, e.g. owns, mentions, depends_on, blocked_by, sourced_from, supersedes, needs_review.
- **Work item:** A source-grounded active unit of work with title, owner, deadline, state, confidence, tags, source quotes, and relationships.
- **Review item:** A work item that needs human attention due to risk, ambiguity, changed owner/deadline, blocker, low confidence, or explicit review language.
- **Chronicle:** Ordered audit trail of ingests and lifecycle updates.

## Functional requirements

- **FR-01 Ingest sources:** Accept source ID, source type, text, timestamp, author, and metadata.
- **FR-02 Extract commitments:** Identify commitments from natural work text, including owners, deadlines, blockers, decisions, risk/review language, projects, and artifacts.
- **FR-03 Ignore noise:** Do not create work items for pure greetings, speculative someday ideas, or conversational filler unless commitment language is present.
- **FR-04 Merge continuity:** Merge fragmented updates into the same work item when they refer to the same topic/project/artifact.
- **FR-05 Preserve provenance:** Every work item must retain source IDs, source types, quotes, and an audit event trail.
- **FR-06 Model graph:** Maintain queryable entities and typed relationships for sources, people, work items, deadlines, blockers, projects, and artifacts.
- **FR-07 Lifecycle tracking:** Support active, blocked, needs_review, done, and stale states with valid transitions.
- **FR-08 Proactive review queue:** Surface curated review items with explicit reasons and source links.
- **FR-09 Persistence:** Store sources, work items, relationships, and events in a local SQLite database.
- **FR-10 Import/export:** Export and import complete work state as JSON without losing provenance.
- **FR-11 CLI:** Provide a local `chronograph` CLI for ingest, list, review, show, graph, export, import, and serve.
- **FR-12 HTTP API:** Provide a stdlib HTTP JSON API for ingesting sources and querying active work, review queue, work item detail, graph neighborhood, and export.
- **FR-13 Search:** Search sources and work items by text.
- **FR-14 Privacy:** Keep all state local unless explicitly exported or pushed by the user.

## Non-functional requirements

- **NFR-01 Local-first:** No mandatory network calls.
- **NFR-02 Dependency-light:** Runtime must work with the Python standard library only.
- **NFR-03 Deterministic:** Extraction should be deterministic and testable.
- **NFR-04 Traceable:** All generated state must be traceable back to sources.
- **NFR-05 Recoverable:** Import/export must preserve enough state to restore a workspace.
- **NFR-06 Usable:** CLI and API responses must be JSON-friendly.

## Acceptance test layers

- Gherkin feature scenarios in `features/chronograph_context.feature`.
- Unit tests for extractor, engine, persistence, import/export, graph, CLI, and API.
- End-to-end tests using temporary SQLite databases.
