#!/usr/bin/env python3
"""Tiny Gherkin acceptance runner for Chronograph's MVP feature grammar."""
from __future__ import annotations

import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronograph import Chronograph, ChronographStore  # noqa: E402
from chronograph.api import create_app  # noqa: E402
from chronograph.cli import build_parser  # noqa: E402


class AcceptanceWorld:
    def __init__(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "acceptance.db"
        self.workspace = Chronograph(ChronographStore(self.db_path))

    @property
    def only_item(self):
        items = self.workspace.work_items()
        assert items, "Expected at least one work item"
        return items[0]

    @property
    def only_review_item(self):
        items = self.workspace.review_items()
        assert items, "Expected at least one review item"
        return items[0]


def parse_feature(path: Path):
    scenarios = []
    current = None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Feature:"):
            continue
        if line.startswith("Scenario:"):
            current = {"name": line, "steps": []}
            scenarios.append(current)
            continue
        if current and re.match(r"^(Given|When|And|Then) ", line):
            current["steps"].append(line)
    return scenarios


def run_step(world: AcceptanceWorld, step: str) -> None:
    if step == "Given an empty Chronograph workspace":
        world.workspace = Chronograph(ChronographStore(world.db_path))
        return

    match = re.match(r'^(?:When|And) I ingest an? (\w+) source "([^"]+)" saying "([^"]+)"$', step)
    if match:
        source_type, source_id, text = match.groups()
        world.workspace.ingest(source_id=source_id, source_type=source_type, text=text)
        return

    match = re.match(r'^Then Chronograph should have (\d+) active work item$', step)
    if match:
        expected = int(match.group(1))
        actual = len(world.workspace.active_work_items())
        assert actual == expected, f"Expected {expected} active item(s), got {actual}"
        return

    match = re.match(r'^And the work item should be titled "([^"]+)"$', step)
    if match:
        assert world.only_item.title == match.group(1)
        return

    match = re.match(r'^And the work item owner should be "([^"]+)"$', step)
    if match:
        assert world.only_item.owner == match.group(1)
        return

    match = re.match(r'^And the work item deadline should be "([^"]+)"$', step)
    if match:
        assert world.only_item.deadline == match.group(1)
        return

    match = re.match(r'^And the work item sources should be "([^"]+)"$', step)
    if match:
        expected = match.group(1).split(",")
        assert world.only_item.source_ids == expected, f"Expected sources {expected}, got {world.only_item.source_ids}"
        return

    match = re.match(r'^(?:Then|And) the work item should include source quote "([^"]+)"$', step)
    if match:
        assert match.group(1) in world.only_item.source_quotes
        return

    match = re.match(r'^And the work item should explain provenance with source "([^"]+)"$', step)
    if match:
        provenance = world.only_item.provenance()
        assert match.group(1) in provenance, provenance
        return

    match = re.match(r'^Then the work item state should be "([^"]+)"$', step)
    if match:
        assert world.only_item.state == match.group(1)
        return

    match = re.match(r'^And the work item blocker should be "([^"]+)"$', step)
    if match:
        assert world.only_item.blocker == match.group(1)
        return

    match = re.match(r'^And Chronograph should report change "([^"]+)"$', step)
    if match:
        assert match.group(1) in world.workspace.recent_changes(), world.workspace.recent_changes()
        return

    match = re.match(r'^Then Chronograph should surface (\d+) review item$', step)
    if match:
        expected = int(match.group(1))
        actual = len(world.workspace.review_items())
        assert actual == expected, f"Expected {expected} review item(s), got {actual}"
        return

    match = re.match(r'^And the review item reason should be "([^"]+)"$', step)
    if match:
        assert world.only_review_item.review_reason == match.group(1)
        return

    if step == "And I reopen the Chronograph workspace":
        world.workspace = Chronograph(ChronographStore(world.db_path))
        return

    if step == "And I export and import the Chronograph workspace":
        payload = world.workspace.export_json()
        world.workspace = Chronograph.import_json(payload, store=ChronographStore(world.db_path))
        return

    match = re.match(r'^And the graph should include relationship "([^"]+) ([a-z_]+) ([^"]+)"$', step)
    if match:
        subject, predicate, object_ = match.groups()
        assert world.workspace.relationship_exists(subject, predicate, object_), world.workspace.relationships()
        return

    match = re.match(r'^Then searching for "([^"]+)" should return source "([^"]+)"$', step)
    if match:
        query, source_id = match.groups()
        sources = world.workspace.search(query)["sources"]
        assert any(source["source_id"] == source_id for source in sources), sources
        return

    match = re.match(
        r'^(?:When|And) I ingest an? (\w+) source "([^"]+)" from "([^"]+)" with metadata "([^"]+)=([^"]+)" saying "([^"]+)"$',
        step,
    )
    if match:
        source_type, source_id, author, mkey, mval, text = match.groups()
        world.workspace.ingest(
            source_id=source_id,
            source_type=source_type,
            text=text,
            author=author,
            metadata={mkey: mval},
        )
        return

    match = re.match(r'^And the source "([^"]+)" author should be "([^"]+)"$', step)
    if match:
        source_id, expected = match.groups()
        source = world.workspace._sources.get(source_id)
        assert source is not None, f"Source {source_id!r} not found"
        assert source.author == expected, f"Expected author {expected!r}, got {source.author!r}"
        return

    match = re.match(r'^And the source "([^"]+)" metadata "([^"]+)" should be "([^"]+)"$', step)
    if match:
        source_id, key, expected = match.groups()
        source = world.workspace._sources.get(source_id)
        assert source is not None, f"Source {source_id!r} not found"
        assert source.metadata.get(key) == expected, f"Expected {key}={expected}, got metadata={source.metadata}"
        return

    if step == "Given the Chronograph CLI":
        world.cli_parser = build_parser()
        return

    match = re.match(r'^(?:Then|And) the CLI should expose command "([^"]+)"$', step)
    if match:
        expected = match.group(1)
        parser = getattr(world, "cli_parser", None)
        assert parser is not None, "Run 'Given the Chronograph CLI' first"
        subcommands: set[str] = set()
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if choices:
                subcommands.update(choices.keys())
        assert expected in subcommands, f"CLI missing subcommand {expected!r}; found {sorted(subcommands)}"
        return

    match = re.match(r'^(?:When|And) I request GET "([^"]+)"$', step)
    if match:
        raw_path = match.group(1)
        path, _, query = raw_path.partition("?")
        app = getattr(world, "api_app", None)
        if app is None:
            app = create_app(world.workspace)
            world.api_app = app
        response_info: dict[str, str] = {}
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "CONTENT_LENGTH": "0",
            "wsgi.input": io.BytesIO(b""),
        }

        def start_response(status: str, headers) -> None:
            response_info["status"] = status

        for chunk in app(environ, start_response):
            del chunk
        world.last_status = response_info.get("status", "")
        return

    match = re.match(r'^Then the HTTP response status should be "([^"]+)"$', step)
    if match:
        expected = match.group(1)
        actual = getattr(world, "last_status", None)
        assert actual == expected, f"Expected status {expected!r}, got {actual!r}"
        return

    if step == "Then the workspace file should exist locally":
        assert world.db_path.exists(), f"Expected SQLite DB at {world.db_path}"
        return

    match = re.match(r'^And the workspace file should contain source "([^"]+)"$', step)
    if match:
        source_id = match.group(1)
        contents = world.db_path.read_bytes()
        assert source_id.encode() in contents, f"Source {source_id!r} not present in {world.db_path}"
        return

    raise AssertionError(f"No step implementation for: {step}")


def main() -> int:
    feature_path = ROOT / "features" / "chronograph_context.feature"
    failures = []
    for scenario in parse_feature(feature_path):
        world = AcceptanceWorld()
        step = "<no steps>"
        try:
            for step in scenario["steps"]:
                run_step(world, step)
            print(f"PASS {scenario['name']}")
        except Exception as exc:  # noqa: BLE001 - human-readable acceptance runner
            failures.append((scenario["name"], step, exc))
            print(f"FAIL {scenario['name']}\n  step: {step}\n  error: {exc}")
    if failures:
        print(f"\n{len(failures)} scenario(s) failed")
        return 1
    print("\nAll acceptance scenarios passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
