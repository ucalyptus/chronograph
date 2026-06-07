import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from chronograph import Chronograph, ChronographStore
from chronograph.extractor import Extractor
from chronograph.api import create_app


class ExtractorTests(unittest.TestCase):
    def test_extracts_owner_deadline_project_and_artifact(self):
        extracted = Extractor().extract("s1", "meeting", "Nina will send launch plan by Wednesday for Project Atlas")
        self.assertEqual(len(extracted), 1)
        item = extracted[0]
        self.assertEqual(item.title, "Launch plan")
        self.assertEqual(item.owner, "Nina")
        self.assertEqual(item.deadline, "Wednesday")
        self.assertIn("Project Atlas", item.projects)
        self.assertIn("launch plan", item.artifacts)

    def test_ignores_speculative_noise(self):
        extracted = Extractor().extract("s2", "meeting", "Great chat. Maybe someday we should redesign the logo.")
        self.assertEqual(extracted, [])

    def test_extracts_done_blocked_and_review_signals(self):
        blocked = Extractor().extract("s3", "slack", "Investor response is blocked on finance numbers")[0]
        self.assertEqual(blocked.state, "blocked")
        self.assertEqual(blocked.blocker, "finance numbers")
        done = Extractor().extract("s4", "task", "Investor response is done")[0]
        self.assertEqual(done.state, "done")
        risky = Extractor().extract("s5", "slack", "Customer follow-up is risky and needs review today")[0]
        self.assertEqual(risky.review_reason, "risky and needs review today")


class ChronographEngineTests(unittest.TestCase):
    def test_merges_fragments_tracks_graph_and_chronicle(self):
        graph = Chronograph()
        graph.ingest("m1", "meeting", "Finance should follow up with the customer")
        graph.ingest("s1", "slack", "Need this by Friday")
        graph.ingest("e1", "email", "Alex owns the finance follow-up now")

        items = graph.active_work_items()
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.title, "Finance follow-up")
        self.assertEqual(item.owner, "Alex")
        self.assertEqual(item.deadline, "Friday")
        self.assertEqual(item.source_ids, ["m1", "s1", "e1"])
        self.assertTrue(graph.relationship_exists("Alex", "owns", "Finance follow-up"))
        self.assertEqual(len(graph.events()), 3)

    def test_review_queue_is_curated(self):
        graph = Chronograph()
        graph.ingest("m4", "meeting", "Sam will send customer follow-up by Friday")
        graph.ingest("s4", "slack", "Customer follow-up is risky and needs review today")
        review = graph.review_items()
        self.assertEqual(len(review), 1)
        self.assertEqual(review[0].review_reason, "risky and needs review today")
        self.assertEqual(review[0].state, "needs_review")

    def test_completion_keeps_history(self):
        graph = Chronograph()
        graph.ingest("t1", "task", "Maya will send renewal quote by Thursday")
        graph.ingest("t2", "task", "Renewal quote is done")
        item = graph.work_items()[0]
        self.assertEqual(item.state, "done")
        self.assertEqual(item.source_ids, ["t1", "t2"])
        self.assertIn("done", graph.recent_changes())

    def test_search_finds_sources_and_work_items(self):
        graph = Chronograph()
        graph.ingest("e2", "email", "Ravi will send customer escalation response by Friday")
        results = graph.search("escalation")
        self.assertEqual(results["sources"][0]["source_id"], "e2")
        self.assertEqual(results["work_items"][0]["title"], "Customer escalation response")


class PersistenceTests(unittest.TestCase):
    def test_sqlite_store_round_trips_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chronograph.db"
            first = Chronograph(store=ChronographStore(path))
            first.ingest("m5", "meeting", "Nina will send launch plan by Wednesday for Project Atlas")

            second = Chronograph(store=ChronographStore(path))
            items = second.active_work_items()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].owner, "Nina")
            self.assertTrue(second.relationship_exists("Nina", "owns", "Launch plan"))

    def test_export_import_preserves_provenance(self):
        graph = Chronograph()
        graph.ingest("d2", "doc", "Omar will review security checklist by Friday")
        payload = graph.export_json()
        restored = Chronograph.import_json(payload)
        item = restored.active_work_items()[0]
        self.assertEqual(item.owner, "Omar")
        self.assertIn("Omar will review security checklist by Friday", item.source_quotes)
        self.assertTrue(restored.relationship_exists("Omar", "owns", "Security checklist"))


class CliTests(unittest.TestCase):
    def test_cli_ingest_list_review_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cg.db"
            env = os.environ | {"PYTHONPATH": "src"}
            base = [sys.executable, "-m", "chronograph.cli", "--db", str(db)]
            ingest = subprocess.run(
                base + ["ingest", "--id", "m1", "--type", "meeting", "--text", "Sam will send customer follow-up by Friday"],
                cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=True,
            )
            self.assertIn("Customer follow-up", ingest.stdout)
            subprocess.run(
                base + ["ingest", "--id", "s1", "--type", "slack", "--text", "Customer follow-up is risky and needs review today"],
                cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=True,
            )
            listed = subprocess.run(base + ["list"], cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=True)
            self.assertIn("Customer follow-up", listed.stdout)
            review = subprocess.run(base + ["review"], cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=True)
            self.assertIn("risky and needs review today", review.stdout)
            exported = subprocess.run(base + ["export"], cwd=Path(__file__).resolve().parents[1], env=env, text=True, capture_output=True, check=True)
            self.assertIn('"sources"', exported.stdout)


class ApiTests(unittest.TestCase):
    def test_wsgi_api_ingest_active_review_and_export(self):
        graph = Chronograph()
        app = create_app(graph)

        def call(method, path, body=None):
            response = {}
            payload = json.dumps(body or {}).encode()
            environ = {
                "REQUEST_METHOD": method,
                "PATH_INFO": path,
                "CONTENT_LENGTH": str(len(payload)),
                "wsgi.input": __import__("io").BytesIO(payload),
            }
            def start_response(status, headers):
                response["status"] = status
                response["headers"] = headers
            data = b"".join(app(environ, start_response)).decode()
            return response["status"], json.loads(data)

        status, created = call("POST", "/sources", {"source_id": "m1", "source_type": "meeting", "text": "Sam will send customer follow-up by Friday"})
        self.assertTrue(status.startswith("201"))
        self.assertEqual(created["work_items"][0]["title"], "Customer follow-up")
        call("POST", "/sources", {"source_id": "s1", "source_type": "slack", "text": "Customer follow-up is risky and needs review today"})
        status, review = call("GET", "/review")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(review[0]["review_reason"], "risky and needs review today")
        status, exported = call("GET", "/export")
        self.assertIn("sources", exported)


if __name__ == "__main__":
    unittest.main()
