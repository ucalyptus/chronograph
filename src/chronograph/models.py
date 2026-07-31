"""Domain models for Chronograph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Source:
    source_id: str
    source_type: str
    text: str
    timestamp: str = field(default_factory=utc_now)
    author: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Source:
        return cls(
            source_id=data["source_id"],
            source_type=data["source_type"],
            text=data["text"],
            timestamp=data.get("timestamp") or utc_now(),
            author=data.get("author"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class Relationship:
    subject: str
    predicate: str
    object: str
    source_id: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Relationship:
        return cls(**data)


@dataclass
class Event:
    event_type: str
    message: str
    source_id: str | None = None
    work_item_id: str | None = None
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        return cls(**data)


@dataclass
class WorkItem:
    title: str
    item_id: str | None = None
    owner: str | None = None
    deadline: str | None = None
    state: str = "active"
    blocker: str | None = None
    review_reason: str | None = None
    confidence: float = 1.0
    tags: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    source_quotes: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.item_id is None:
            self.item_id = self.slugify(self.title)

    @staticmethod
    def slugify(value: str) -> str:
        import re

        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "work-item"

    def add_source(self, source: Source) -> None:
        if source.source_id not in self.source_ids:
            self.source_ids.append(source.source_id)
            self.source_quotes.append(source.text)
            self.source_types.append(source.source_type)
            self.updated_at = utc_now()

    def provenance(self) -> str:
        return ", ".join(
            f"{sid} ({stype})"
            for sid, stype in zip(self.source_ids, self.source_types, strict=False)
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkItem:
        return cls(**data)
