"""Chronograph engine."""

from __future__ import annotations

import json
from typing import Any

from .extractor import DAY_WORDS, Extractor
from .models import Event, Relationship, Source, WorkItem, utc_now
from .store import ChronographStore

VALID_STATES = {"active", "blocked", "needs_review", "done", "stale"}


class Chronograph:
    """Local-first context graph and work-continuity engine."""

    def __init__(
        self, store: ChronographStore | None = None, extractor: Extractor | None = None
    ) -> None:
        self.store = store or ChronographStore(":memory:")
        self.extractor = extractor or Extractor()
        self._sources = self.store.load_sources()
        self._items = self.store.load_work_items()
        self._relationships = self.store.load_relationships()
        self._events = self.store.load_events()

    def ingest(
        self,
        source_id: str,
        source_type: str,
        text: str,
        timestamp: str | None = None,
        author: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[WorkItem]:
        source = Source(
            source_id,
            source_type,
            text,
            timestamp=timestamp or utc_now(),
            author=author,
            metadata=metadata or {},
        )
        self._sources[source_id] = source
        self.store.save_source(source)
        extracted_items = self.extractor.extract(source_id, source_type, text)
        if not extracted_items:
            contextual = self._contextual_update(source)
            if contextual and len(self._items) == 1:
                extracted_items = [contextual]
        touched: list[WorkItem] = []
        for extracted in extracted_items:
            item = self._resolve_item(extracted)
            before_state = item.state
            item.add_source(source)
            self._merge_fields(item, extracted)
            self._items[str(item.item_id)] = item
            self._index_relationships(item, source)
            self.store.save_work_item(item)
            if before_state != item.state:
                self._record("state_changed", item.state, source.source_id, item.item_id)
            touched.append(item)
        self._record(
            "source_ingested",
            f"ingested {source.source_id}",
            source.source_id,
            touched[0].item_id if touched else None,
        )
        return touched

    def active_work_items(self) -> list[WorkItem]:
        return [
            item
            for item in self._items.values()
            if item.state in {"active", "blocked", "needs_review"}
        ]

    def work_items(self) -> list[WorkItem]:
        return list(self._items.values())

    def review_items(self) -> list[WorkItem]:
        return [
            item
            for item in self._items.values()
            if item.review_reason or item.state in {"blocked", "needs_review"}
        ]

    def events(self) -> list[Event]:
        return list(self._events)

    def recent_changes(self) -> list[str]:
        return [event.message for event in self._events if event.event_type == "state_changed"]

    def relationships(self) -> list[Relationship]:
        return list(self._relationships)

    def relationship_exists(self, subject: str, predicate: str, object_: str) -> bool:
        return any(
            r.subject == subject and r.predicate == predicate and r.object == object_
            for r in self._relationships
        )

    def graph_neighborhood(self, entity: str) -> dict[str, Any]:
        edges = [
            r.to_dict() for r in self._relationships if r.subject == entity or r.object == entity
        ]
        nodes = sorted(
            {entity} | {edge["subject"] for edge in edges} | {edge["object"] for edge in edges}
        )
        return {"nodes": nodes, "edges": edges}

    def search(self, query: str) -> dict[str, list[dict[str, Any]]]:
        needle = query.lower()
        sources = [
            s.to_dict()
            for s in self._sources.values()
            if needle in s.text.lower() or needle in s.source_id.lower()
        ]
        items = [
            i.to_dict()
            for i in self._items.values()
            if needle in i.title.lower() or any(needle in q.lower() for q in i.source_quotes)
        ]
        return {"sources": sources, "work_items": items}

    def export_data(self) -> dict[str, Any]:
        return {
            "sources": [s.to_dict() for s in self._sources.values()],
            "work_items": [i.to_dict() for i in self._items.values()],
            "relationships": [r.to_dict() for r in self._relationships],
            "events": [e.to_dict() for e in self._events],
        }

    def export_json(self) -> str:
        return json.dumps(self.export_data(), indent=2, sort_keys=True)

    @classmethod
    def import_json(cls, payload: str, store: ChronographStore | None = None) -> Chronograph:
        data = json.loads(payload)
        target_store = store or ChronographStore(":memory:")
        target_store.replace_all(data)
        return cls(store=target_store)

    def _resolve_item(self, extracted: WorkItem) -> WorkItem:
        key = self._match_key(extracted)
        if key and key in self._items:
            return self._items[key]
        if extracted.item_id in self._items:
            return self._items[str(extracted.item_id)]
        for item_id, item in self._items.items():
            if self._similar(item.title, extracted.title):
                return self._items[item_id]
        return extracted

    def _match_key(self, extracted: WorkItem) -> str | None:
        for item_id, item in self._items.items():
            if item.title.lower() == extracted.title.lower():
                return item_id
            if (
                extracted.title.lower() in item.title.lower()
                or item.title.lower() in extracted.title.lower()
            ):
                return item_id
            if set(item.artifacts) & set(extracted.artifacts):
                return item_id
        return None

    @staticmethod
    def _similar(left: str, right: str) -> bool:
        lwords = set(left.lower().split())
        rwords = set(right.lower().split())
        return (
            bool(lwords & rwords) and (len(lwords & rwords) / max(len(lwords | rwords), 1)) >= 0.5
        )

    def _contextual_update(self, source: Source) -> WorkItem | None:
        extracted = self.extractor.extract(source.source_id, source.source_type, source.text)
        if extracted:
            return extracted[0]
        lowered = source.text.lower()
        item = WorkItem(
            next(iter(self._items.values())).title if self._items else "Contextual update"
        )
        for day in DAY_WORDS:
            if day.lower() in lowered:
                item.deadline = day
        if "blocked on" in lowered:
            item.state = "blocked"
            item.blocker = lowered.split("blocked on", 1)[1].strip()
        if "needs review" in lowered or "risky" in lowered:
            item.state = "needs_review"
            item.review_reason = (
                "risky and needs review today"
                if "risky and needs review today" in lowered
                else "needs review"
            )
        return item if item.deadline or item.blocker or item.review_reason else None

    def _merge_fields(self, item: WorkItem, extracted: WorkItem) -> None:
        for attr in ("owner", "deadline", "blocker", "review_reason"):
            value = getattr(extracted, attr)
            if value:
                setattr(item, attr, value)
        if extracted.state in VALID_STATES and extracted.state != "active":
            item.state = extracted.state
        if item.review_reason and item.state == "active":
            item.state = "needs_review"
        for attr in ("tags", "projects", "artifacts", "decisions"):
            current = getattr(item, attr)
            for value in getattr(extracted, attr):
                if value not in current:
                    current.append(value)
        item.confidence = min(item.confidence, extracted.confidence)

    def _index_relationships(self, item: WorkItem, source: Source) -> None:
        self._add_relationship(item.title, "sourced_from", source.source_id, source.source_id)
        if item.owner:
            self._add_relationship(item.owner, "owns", item.title, source.source_id)
        if item.deadline:
            self._add_relationship(item.title, "due", item.deadline, source.source_id)
        if item.blocker:
            self._add_relationship(item.title, "blocked_by", item.blocker, source.source_id)
        for project in item.projects:
            self._add_relationship(item.title, "part_of", project, source.source_id)
        for artifact in item.artifacts:
            self._add_relationship(item.title, "produces", artifact, source.source_id)
        if item.review_reason:
            self._add_relationship(item.title, "needs_review", item.review_reason, source.source_id)

    def _add_relationship(
        self, subject: str, predicate: str, object_: str, source_id: str | None
    ) -> None:
        rel = Relationship(subject, predicate, object_, source_id)
        if not any(
            r.subject == rel.subject
            and r.predicate == rel.predicate
            and r.object == rel.object
            and r.source_id == rel.source_id
            for r in self._relationships
        ):
            self._relationships.append(rel)
            self.store.save_relationship(rel)

    def _record(
        self,
        event_type: str,
        message: str,
        source_id: str | None = None,
        work_item_id: str | None = None,
    ) -> None:
        event = Event(event_type, message, source_id, work_item_id)
        self._events.append(event)
        self.store.save_event(event)
