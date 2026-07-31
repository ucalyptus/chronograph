"""Command line interface for Chronograph."""

from __future__ import annotations

import argparse
import json
import sys

from .api import serve
from .engine import Chronograph
from .store import ChronographStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chronograph")
    parser.add_argument("--db", default="chronograph.db", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="ingest a source")
    ingest.add_argument("--id", required=True, dest="source_id")
    ingest.add_argument("--type", required=True, dest="source_type")
    ingest.add_argument("--text", required=True)
    ingest.add_argument("--author")

    sub.add_parser("list", help="list all work items")
    sub.add_parser("active", help="list active work items")
    sub.add_parser("review", help="list review queue")

    show = sub.add_parser("show", help="show a graph neighborhood")
    show.add_argument("entity")

    search = sub.add_parser("search", help="search sources and work items")
    search.add_argument("query")

    sub.add_parser("export", help="export complete state as JSON")

    imp = sub.add_parser("import", help="import complete state from JSON file")
    imp.add_argument("path")

    http = sub.add_parser("serve", help="serve HTTP JSON API")
    http.add_argument("--host", default="127.0.0.1")
    http.add_argument("--port", type=int, default=8765)
    return parser


def _print(payload) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        serve(args.db, args.host, args.port)
        return 0
    graph = Chronograph(ChronographStore(args.db))
    if args.command == "ingest":
        items = graph.ingest(args.source_id, args.source_type, args.text, author=args.author)
        _print({"work_items": [item.to_dict() for item in items]})
        return 0
    if args.command == "list":
        _print([item.to_dict() for item in graph.work_items()])
        return 0
    if args.command == "active":
        _print([item.to_dict() for item in graph.active_work_items()])
        return 0
    if args.command == "review":
        _print([item.to_dict() for item in graph.review_items()])
        return 0
    if args.command == "show":
        _print(graph.graph_neighborhood(args.entity))
        return 0
    if args.command == "search":
        _print(graph.search(args.query))
        return 0
    if args.command == "export":
        print(graph.export_json())
        return 0
    if args.command == "import":
        with open(args.path, encoding="utf-8") as fh:
            Chronograph.import_json(fh.read(), store=ChronographStore(args.db))
        _print({"imported": True})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
