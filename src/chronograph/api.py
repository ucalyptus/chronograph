"""Stdlib WSGI JSON API for Chronograph."""

from __future__ import annotations

import json
from collections.abc import Callable
from wsgiref.simple_server import make_server

from .engine import Chronograph
from .store import ChronographStore


def _json_response(start_response: Callable, status: str, payload) -> list[bytes]:
    body = json.dumps(payload, sort_keys=True).encode()
    start_response(
        status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]
    )
    return [body]


def create_app(graph: Chronograph | None = None):
    chronograph = graph or Chronograph()

    def app(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        body = environ["wsgi.input"].read(length) if length else b""
        try:
            payload = json.loads(body.decode()) if body else {}
        except json.JSONDecodeError:
            return _json_response(start_response, "400 Bad Request", {"error": "invalid json"})

        if method == "GET" and path == "/health":
            return _json_response(start_response, "200 OK", {"ok": True})
        if method == "POST" and path == "/sources":
            required = {"source_id", "source_type", "text"}
            if not required <= set(payload):
                return _json_response(
                    start_response,
                    "400 Bad Request",
                    {"error": "source_id, source_type, and text are required"},
                )
            items = chronograph.ingest(
                payload["source_id"],
                payload["source_type"],
                payload["text"],
                timestamp=payload.get("timestamp"),
                author=payload.get("author"),
                metadata=payload.get("metadata") or {},
            )
            return _json_response(
                start_response, "201 Created", {"work_items": [item.to_dict() for item in items]}
            )
        if method == "GET" and path == "/work-items":
            return _json_response(
                start_response, "200 OK", [item.to_dict() for item in chronograph.work_items()]
            )
        if method == "GET" and path == "/active":
            return _json_response(
                start_response,
                "200 OK",
                [item.to_dict() for item in chronograph.active_work_items()],
            )
        if method == "GET" and path == "/review":
            return _json_response(
                start_response, "200 OK", [item.to_dict() for item in chronograph.review_items()]
            )
        if method == "GET" and path.startswith("/search"):
            query = ""
            raw_query = environ.get("QUERY_STRING", "")
            for part in raw_query.split("&"):
                if part.startswith("q="):
                    from urllib.parse import unquote_plus

                    query = unquote_plus(part[2:])
            return _json_response(start_response, "200 OK", chronograph.search(query))
        if method == "GET" and path.startswith("/graph/"):
            from urllib.parse import unquote

            entity = unquote(path.split("/graph/", 1)[1])
            return _json_response(start_response, "200 OK", chronograph.graph_neighborhood(entity))
        if method == "GET" and path == "/export":
            return _json_response(start_response, "200 OK", chronograph.export_data())
        return _json_response(start_response, "404 Not Found", {"error": "not found"})

    return app


def serve(db: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = create_app(Chronograph(ChronographStore(db)))
    with make_server(host, port, app) as server:
        print(f"Chronograph API listening on http://{host}:{port}")
        server.serve_forever()
