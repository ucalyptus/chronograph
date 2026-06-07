"""Deterministic commitment extraction for Chronograph."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .models import WorkItem

DAY_WORDS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
KNOWN_TOPICS = {
    "finance follow-up": "Finance follow-up",
    "board memo": "Board memo",
    "data center report": "Data center report",
    "investor response": "Investor response",
    "customer follow-up": "Customer follow-up",
    "launch plan": "Launch plan",
    "security checklist": "Security checklist",
    "renewal quote": "Renewal quote",
    "customer escalation response": "Customer escalation response",
}
NOISE_PATTERNS = ("great chat", "thanks everyone", "fyi only", "no action")
SPECULATIVE_PATTERNS = ("maybe someday", "someday", "eventually we should")
COMMITMENT_SIGNALS = ("will", "should", "owns", "need", "blocked", "review", "risky", "done", "due")


@dataclass
class Extractor:
    """Rules-based extractor designed for deterministic local behavior."""

    def extract(self, source_id: str, source_type: str, text: str) -> list[WorkItem]:
        del source_id, source_type
        work_items: list[WorkItem] = []
        for sentence in self._sentences(text):
            lowered = sentence.lower()
            if self._is_noise(lowered):
                continue
            title = self._extract_title(lowered)
            if not title:
                continue
            item = WorkItem(title=title)
            item.owner = self._extract_owner(sentence)
            item.deadline = self._extract_deadline(sentence)
            item.projects = self._extract_projects(sentence)
            item.artifacts = self._extract_artifacts(title)
            item.blocker = self._extract_blocker(lowered)
            item.review_reason = self._extract_review_reason(lowered)
            item.decisions = self._extract_decisions(sentence)
            if item.blocker:
                item.state = "blocked"
            if self._extract_done(lowered):
                item.state = "done"
            if item.review_reason and item.state != "done":
                item.state = "needs_review"
            work_items.append(item)
        return self._dedupe(work_items)

    @staticmethod
    def _sentences(text: str) -> list[str]:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        return parts or [text.strip()]

    @staticmethod
    def _is_noise(lowered: str) -> bool:
        if any(signal in lowered for signal in COMMITMENT_SIGNALS):
            return False
        return any(pattern in lowered for pattern in NOISE_PATTERNS + SPECULATIVE_PATTERNS)

    @staticmethod
    def _extract_title(lowered: str) -> str | None:
        follow_up_match = re.search(r"([a-z]+) should follow up", lowered)
        if follow_up_match:
            return f"{follow_up_match.group(1).capitalize()} follow-up"
        for topic, display in KNOWN_TOPICS.items():
            if topic in lowered:
                return display
        if re.fullmatch(r"need this by [a-z]+", lowered.strip()):
            return None
        patterns = [
            r"([a-z]+) should follow up",
            r"send (?:the )?([a-z ]+?)(?: by| for|$)",
            r"review (?:the )?([a-z ]+?)(?: by| for|$)",
            r"owns (?:the )?([a-z ]+?)(?: by| now|$)",
            r"([a-z ]+?) is blocked on",
            r"([a-z ]+?) is risky",
            r"([a-z ]+?) is done",
            r"need (?:this|the )?([a-z ]+?)(?: by|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                raw = match.group(1).strip()
                raw = re.sub(r"^(the|a|an)\s+", "", raw)
                if raw in {"this", "it"} or len(raw) < 3:
                    continue
                return raw.capitalize()
        return None

    @staticmethod
    def _extract_owner(sentence: str) -> str | None:
        patterns = [
            r"\b([A-Z][a-z]+)\s+will\b",
            r"\b([A-Z][a-z]+)\s+owns\b",
            r"\b([A-Z][a-z]+)\s+is now owner\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, sentence)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_deadline(text: str) -> str | None:
        for day in DAY_WORDS:
            if re.search(rf"\b{day}\b", text, re.IGNORECASE):
                return day
        match = re.search(r"by (today|tomorrow|end of week|eow)", text, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def _extract_projects(text: str) -> list[str]:
        return re.findall(r"Project\s+[A-Z][A-Za-z0-9_-]+", text)

    @staticmethod
    def _extract_artifacts(title: str) -> list[str]:
        artifact_terms = ("plan", "memo", "report", "checklist", "quote", "response", "follow-up")
        return [title.lower()] if any(term in title.lower() for term in artifact_terms) else []

    @staticmethod
    def _extract_blocker(lowered: str) -> str | None:
        match = re.search(r"blocked on ([a-z0-9 _-]+)", lowered)
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_review_reason(lowered: str) -> str | None:
        if "risky and needs review today" in lowered:
            return "risky and needs review today"
        match = re.search(r"(risky|needs review(?: today)?|ambiguous|low confidence)", lowered)
        return match.group(1) if match else None

    @staticmethod
    def _extract_done(lowered: str) -> bool:
        return bool(re.search(r"\b(done|completed|closed|finished)\b", lowered))

    @staticmethod
    def _extract_decisions(sentence: str) -> list[str]:
        if "decided" in sentence.lower() or "decision" in sentence.lower():
            return [sentence]
        return []

    @staticmethod
    def _dedupe(items: list[WorkItem]) -> list[WorkItem]:
        seen = set()
        result = []
        for item in items:
            key = item.title.lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result
