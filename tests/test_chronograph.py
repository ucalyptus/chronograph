import unittest

from chronograph import Chronograph


class ChronographUnitTests(unittest.TestCase):
    def test_merges_fragments_by_topic_into_one_active_work_item(self):
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

    def test_curates_real_commitments_and_ignores_speculative_noise(self):
        graph = Chronograph()

        graph.ingest(
            "m2",
            "meeting",
            "Great chat everyone. Sarah will send the board memo by Tuesday. Maybe someday we should redesign the logo.",
        )

        items = graph.active_work_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Board memo")
        self.assertEqual(items[0].owner, "Sarah")
        self.assertEqual(items[0].deadline, "Tuesday")

    def test_keeps_source_quotes_and_provenance(self):
        graph = Chronograph()
        quote = "Liam will review the data center report by Monday"

        graph.ingest("d1", "doc", quote)

        item = graph.active_work_items()[0]
        self.assertIn(quote, item.source_quotes)
        self.assertIn("d1", item.provenance())
        self.assertIn("doc", item.provenance())

    def test_tracks_blocked_state_and_recent_changes(self):
        graph = Chronograph()

        graph.ingest("m3", "meeting", "Priya owns the investor response by Thursday")
        graph.ingest("s3", "slack", "Investor response is blocked on finance numbers")

        item = graph.active_work_items()[0]
        self.assertEqual(item.state, "blocked")
        self.assertEqual(item.blocker, "finance numbers")
        self.assertIn("blocked", graph.recent_changes())

    def test_surfaces_review_items_with_reason(self):
        graph = Chronograph()

        graph.ingest("m4", "meeting", "Sam will send customer follow-up by Friday")
        graph.ingest("s4", "slack", "Customer follow-up is risky and needs review today")

        review_items = graph.review_items()
        self.assertEqual(len(review_items), 1)
        self.assertEqual(review_items[0].review_reason, "risky and needs review today")

    def test_sandbox_local_instances_do_not_share_state(self):
        first = Chronograph()
        second = Chronograph()

        first.ingest("m5", "meeting", "Nina will send customer follow-up by Monday")

        self.assertEqual(len(first.active_work_items()), 1)
        self.assertEqual(second.active_work_items(), [])


if __name__ == "__main__":
    unittest.main()
