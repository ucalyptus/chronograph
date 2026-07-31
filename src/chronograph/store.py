"""SQLite persistence for Chronograph."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import Event, Relationship, Source, WorkItem


class ChronographStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        # check_same_thread=False lets the same connection be used across threads
        # (needed when `chronograph serve` runs the WSGI server in a background
        # thread — e.g. under wsgiref.simple_server driven by tests, or under a
        # threading harness). Chronograph is single-writer by design, so the
        # sqlite3 driver's per-thread guard is unnecessary friction here.
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS work_items (
                item_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                source_id TEXT,
                confidence REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def save_source(self, source: Source) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO sources(source_id, payload) VALUES (?, ?)",
            (source.source_id, json.dumps(source.to_dict(), sort_keys=True)),
        )
        self.connection.commit()

    def save_work_item(self, item: WorkItem) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO work_items(item_id, payload) VALUES (?, ?)",
            (item.item_id, json.dumps(item.to_dict(), sort_keys=True)),
        )
        self.connection.commit()

    def save_relationship(self, relationship: Relationship) -> None:
        rel_id = json.dumps([relationship.subject, relationship.predicate, relationship.object, relationship.source_id], sort_keys=True)
        self.connection.execute(
            "INSERT OR REPLACE INTO relationships(id, subject, predicate, object, source_id, confidence) VALUES (?, ?, ?, ?, ?, ?)",
            (rel_id, relationship.subject, relationship.predicate, relationship.object, relationship.source_id, relationship.confidence),
        )
        self.connection.commit()

    def save_event(self, event: Event) -> None:
        self.connection.execute("INSERT INTO events(payload) VALUES (?)", (json.dumps(event.to_dict(), sort_keys=True),))
        self.connection.commit()

    def load_sources(self) -> dict[str, Source]:
        rows = self.connection.execute("SELECT payload FROM sources ORDER BY source_id").fetchall()
        return {source.source_id: source for source in (Source.from_dict(json.loads(row["payload"])) for row in rows)}

    def load_work_items(self) -> dict[str, WorkItem]:
        rows = self.connection.execute("SELECT payload FROM work_items ORDER BY rowid").fetchall()
        return {str(item.item_id): item for item in (WorkItem.from_dict(json.loads(row["payload"])) for row in rows)}

    def load_relationships(self) -> list[Relationship]:
        rows = self.connection.execute("SELECT subject, predicate, object, source_id, confidence FROM relationships ORDER BY rowid").fetchall()
        return [Relationship(row["subject"], row["predicate"], row["object"], row["source_id"], row["confidence"]) for row in rows]

    def load_events(self) -> list[Event]:
        rows = self.connection.execute("SELECT payload FROM events ORDER BY id").fetchall()
        return [Event.from_dict(json.loads(row["payload"])) for row in rows]

    def replace_all(self, payload: dict[str, Any]) -> None:
        self.connection.executescript("DELETE FROM sources; DELETE FROM work_items; DELETE FROM relationships; DELETE FROM events;")
        for data in payload.get("sources", []):
            self.save_source(Source.from_dict(data))
        for data in payload.get("work_items", []):
            self.save_work_item(WorkItem.from_dict(data))
        for data in payload.get("relationships", []):
            self.save_relationship(Relationship.from_dict(data))
        for data in payload.get("events", []):
            self.save_event(Event.from_dict(data))

    def close(self) -> None:
        self.connection.close()
