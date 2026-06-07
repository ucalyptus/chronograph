"""Chronograph: source-grounded context graph and task extraction MVP."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable


DAY_WORDS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
TOPIC_WORDS = (
    "finance follow-up",
    "board memo",
    "data center report",
    "investor response",
    "customer follow-up",
)


@dataclass(frozen=True)
class Source:
    """Raw source material ingested into a sandbox-local workspace."""

    source_id: str
    source_type: str
    text: str


@dataclass
class WorkItem:
    """Structured active work item built from one or more source fragments."""

    title: str
    source_ids: list[str] = field(default_factory=list)
    source_quotes: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    owner: str | None = None
    deadline: str | None = None
    state: str = "active"
    blocker: str | None = None
    review_reason: str | None = None

    def add_source(self, source: Source) -> None:
        if source.source_id not in self.source_ids:
            self.source_ids.append(source.source_id)
            self.source_quotes.append(source.text)
            self.source_types.append(source.source_type)

    def provenance(self) -> str:
        parts = [f"{source_id} ({source_type})" for source_id, source_type in zip(self.source_ids, self.source_types)]
        return ", ".join(parts)


class Chronograph:
    """A sandbox-local context graph for extracting and tracking active work."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}
        self._items: dict[str, WorkItem] = {}
        self._changes: list[str] = []

    def ingest(self, source_id: str, source_type: str, text: str) -> None:
        """Ingest source text and update structured active work state."""
        source = Source(source_id=source_id, source_type=source_type, text=text)
        self._sources[source_id] = source
        extracted_items = list(self._extract_work_items(source))
        if not extracted_items:
            contextual_update = self._extract_contextual_update(source)
            if contextual_update and len(self._items) == 1:
                item = next(iter(self._items.values()))
                item.add_source(source)
                self._merge_item_fields(item, contextual_update)
            return
        for extracted in extracted_items:
            item = self._items.setdefault(extracted.title.lower(), WorkItem(title=extracted.title))
            item.add_source(source)
            self._merge_item_fields(item, extracted)

    def active_work_items(self) -> list[WorkItem]:
        """Return curated active work items in creation order."""
        return list(self._items.values())

    def review_items(self) -> list[WorkItem]:
        """Return active work items requiring human review."""
        return [item for item in self._items.values() if item.review_reason]

    def recent_changes(self) -> list[str]:
        """Return recent state changes, newest last."""
        return list(self._changes)

    def _extract_work_items(self, source: Source) -> Iterable[WorkItem]:
        text = source.text
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        for sentence in sentences or [text]:
            lowered = sentence.lower()
            if self._is_noise(lowered):
                continue
            title = self._extract_title(lowered)
            if not title:
                continue
            item = WorkItem(title=title)
            owner = self._extract_owner(sentence, lowered)
            if owner:
                item.owner = owner
            deadline = self._extract_deadline(sentence)
            if deadline:
                item.deadline = deadline
            blocker = self._extract_blocker(lowered)
            if blocker:
                item.state = "blocked"
                item.blocker = blocker
            review_reason = self._extract_review_reason(lowered)
            if review_reason:
                item.review_reason = review_reason
            yield item

    def _extract_contextual_update(self, source: Source) -> WorkItem | None:
        text = source.text
        lowered = text.lower()
        item = WorkItem(title="Contextual update")
        deadline = self._extract_deadline(text)
        blocker = self._extract_blocker(lowered)
        review_reason = self._extract_review_reason(lowered)
        if deadline:
            item.deadline = deadline
        if blocker:
            item.state = "blocked"
            item.blocker = blocker
        if review_reason:
            item.review_reason = review_reason
        if deadline or blocker or review_reason:
            return item
        return None

    def _merge_item_fields(self, item: WorkItem, extracted: WorkItem) -> None:
        if extracted.owner:
            item.owner = extracted.owner
        if extracted.deadline:
            item.deadline = extracted.deadline
        if extracted.blocker:
            item.blocker = extracted.blocker
        if extracted.state != item.state:
            item.state = extracted.state
            self._changes.append(extracted.state)
        if extracted.review_reason:
            item.review_reason = extracted.review_reason

    @staticmethod
    def _is_noise(lowered: str) -> bool:
        speculative = ("maybe someday", "someday", "great chat")
        has_commitment_signal = any(signal in lowered for signal in ("will", "should", "owns", "need", "blocked", "review", "risky"))
        return any(token in lowered for token in speculative) and not has_commitment_signal

    @staticmethod
    def _extract_title(lowered: str) -> str | None:
        explicit_titles = {
            "finance follow-up": "Finance follow-up",
            "board memo": "Board memo",
            "data center report": "Data center report",
            "investor response": "Investor response",
            "customer follow-up": "Customer follow-up",
        }
        for topic, display in explicit_titles.items():
            if topic in lowered:
                return display
        follow_up_match = re.search(r"([a-z]+) should follow up", lowered)
        if follow_up_match:
            return f"{follow_up_match.group(1).title()} follow-up"
        memo_match = re.search(r"send the ([a-z ]+ memo)", lowered)
        if memo_match:
            return memo_match.group(1).title()
        report_match = re.search(r"review the ([a-z ]+ report)", lowered)
        if report_match:
            return report_match.group(1).title()
        response_match = re.search(r"owns the ([a-z ]+ response)", lowered)
        if response_match:
            return response_match.group(1).title()
        return None

    @staticmethod
    def _extract_owner(sentence: str, lowered: str) -> str | None:
        owner_patterns = (
            r"\b([A-Z][a-z]+)\s+will\b",
            r"\b([A-Z][a-z]+)\s+owns\b",
            r"\b([A-Z][a-z]+)\s+is now owner\b",
            r"\b([A-Z][a-z]+)\s+owns the\b",
        )
        for pattern in owner_patterns:
            match = re.search(pattern, sentence)
            if match:
                return match.group(1)
        reverse_owner = re.search(r"\b([A-Z][a-z]+) owns the", sentence)
        if reverse_owner:
            return reverse_owner.group(1)
        now_owner = re.search(r"\b([A-Z][a-z]+) owns .* now", sentence)
        if now_owner:
            return now_owner.group(1)
        return None

    @staticmethod
    def _extract_deadline(text: str) -> str | None:
        for day in DAY_WORDS:
            if re.search(rf"\b{day}\b", text, flags=re.IGNORECASE):
                return day
        return None

    @staticmethod
    def _extract_blocker(lowered: str) -> str | None:
        match = re.search(r"blocked on ([a-z ]+)", lowered)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _extract_review_reason(lowered: str) -> str | None:
        if "risky and needs review today" in lowered:
            return "risky and needs review today"
        if "needs review" in lowered:
            return lowered[lowered.index("needs review") :].strip()
        return None
