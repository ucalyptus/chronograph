"""End-to-end tests: real socket for the HTTP API and full subprocess flow for CLI subcommands.

Covers Worker B's B-E-01..08 findings — the previous ApiTests use an in-process WSGI
call, which swarmforge classifies as integration, not E2E. Here we bind a real socket
via wsgiref.simple_server on an ephemeral port and drive it with urllib.request.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from wsgiref.simple_server import make_server

from chronograph import Chronograph
from chronograph.api import create_app

REPO_ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RealSocketApiE2ETests(unittest.TestCase):
    """Drive the HTTP API through a real socket via wsgiref.simple_server."""

    def setUp(self) -> None:
        self.graph = Chronograph()
        self.app = create_app(self.graph)
        self.port = _free_port()
        self.server = make_server("127.0.0.1", self.port, self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _get(self, path: str):
        with urllib.request.urlopen(self._url(path), timeout=5) as response:
            return response.status, json.loads(response.read())

    def _post(self, path: str, body: dict):
        request = urllib.request.Request(
            self._url(path),
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())

    def test_health_over_real_http(self):
        status, body = self._get("/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_full_ingest_query_export_round_trip(self):
        status, created = self._post(
            "/sources",
            {"source_id": "e1", "source_type": "meeting", "text": "Nina will send launch plan by Wednesday for Project Atlas"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["work_items"][0]["title"], "Launch plan")

        status, active = self._get("/active")
        self.assertEqual(status, 200)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["owner"], "Nina")

        status, all_items = self._get("/work-items")
        self.assertEqual(status, 200)
        self.assertEqual(len(all_items), 1)

        status, review = self._get("/review")
        self.assertEqual(status, 200)
        self.assertEqual(review, [])

        status, search = self._get("/search?q=launch")
        self.assertEqual(status, 200)
        self.assertEqual(search["work_items"][0]["title"], "Launch plan")

        status, graph = self._get("/graph/Nina")
        self.assertEqual(status, 200)
        self.assertIn("Nina", graph["nodes"])
        self.assertTrue(any(edge["predicate"] == "owns" for edge in graph["edges"]))

        status, exported = self._get("/export")
        self.assertEqual(status, 200)
        self.assertIn("sources", exported)
        self.assertEqual(len(exported["sources"]), 1)

    def test_invalid_json_rejected_with_400(self):
        request = urllib.request.Request(
            self._url("/sources"),
            data=b"{not json",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

    def test_missing_required_fields_rejected_with_400(self):
        request = urllib.request.Request(
            self._url("/sources"),
            data=json.dumps({"source_id": "x"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(ctx.exception.code, 400)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self._url("/does-not-exist"), timeout=5)
        self.assertEqual(ctx.exception.code, 404)


class CliServeSubprocessE2ETests(unittest.TestCase):
    """Actually spawn `chronograph serve` and hit it over a real socket."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "e2e.db")
        self.port = _free_port()
        env = {**os.environ, "PYTHONPATH": "src"}
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "chronograph.cli",
                "--db",
                self.db,
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=0.3) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        self.tearDown()
        self.fail("chronograph serve did not start in time")

    def tearDown(self) -> None:
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            pass
        finally:
            for stream in (self.proc.stdout, self.proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
        self.tmp.cleanup()

    def test_live_process_serves_health_and_survives_ingest(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(json.loads(response.read())["ok"])

        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/sources",
            data=json.dumps({"source_id": "e1", "source_type": "meeting", "text": "Nina will send launch plan by Friday"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 201)

        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/active", timeout=5) as response:
            body = json.loads(response.read())
        self.assertEqual(len(body), 1)


class CliSubcommandE2ETests(unittest.TestCase):
    """Cover CLI subcommands that weren't previously E2E-tested: active, show, search, import."""

    def _run(self, args, cwd):
        env = {**os.environ, "PYTHONPATH": "src"}
        return subprocess.run(
            [sys.executable, "-m", "chronograph.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_active_show_search_export_and_import_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cli.db"
            base = ["--db", str(db)]
            cwd = REPO_ROOT

            self._run(
                base
                + [
                    "ingest",
                    "--id",
                    "m1",
                    "--type",
                    "meeting",
                    "--text",
                    "Nina will send launch plan by Wednesday for Project Atlas",
                ],
                cwd,
            )
            self._run(
                base
                + [
                    "ingest",
                    "--id",
                    "s1",
                    "--type",
                    "slack",
                    "--text",
                    "Launch plan is risky and needs review today",
                ],
                cwd,
            )

            active = self._run(base + ["active"], cwd).stdout
            self.assertIn("Launch plan", active)

            show = self._run(base + ["show", "Nina"], cwd).stdout
            self.assertIn("Nina", show)
            self.assertIn("owns", show)

            search = self._run(base + ["search", "launch"], cwd).stdout
            self.assertIn("Launch plan", search)

            exported = self._run(base + ["export"], cwd).stdout
            payload_path = Path(tmp) / "payload.json"
            payload_path.write_text(exported)

            db2 = Path(tmp) / "cli2.db"
            base2 = ["--db", str(db2)]
            imported = self._run(base2 + ["import", str(payload_path)], cwd).stdout
            self.assertIn('"imported": true', imported)

            active2 = self._run(base2 + ["active"], cwd).stdout
            self.assertIn("Launch plan", active2)


if __name__ == "__main__":
    unittest.main()
