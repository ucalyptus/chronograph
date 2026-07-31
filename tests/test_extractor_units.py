"""Unit tests pinning individual Extractor helpers and engine invariants.

Every pure helper in `Extractor` and every branching helper in
`Chronograph` (as identified by the SDLC audit) gets a dedicated test
here, independent of the higher-level integration paths in
`tests/test_full_system.py`.
"""

import unittest

from chronograph import Chronograph
from chronograph.extractor import DAY_WORDS, KNOWN_TOPICS, Extractor
from chronograph.models import WorkItem


class SentencesTests(unittest.TestCase):
    def test_splits_on_punctuation_and_strips(self):
        result = Extractor._sentences("Hello world. This is fine!  Bye.")
        self.assertEqual(result, ["Hello world.", "This is fine!", "Bye."])

    def test_returns_whole_stripped_text_when_no_terminator(self):
        self.assertEqual(Extractor._sentences("  no terminator here  "), ["no terminator here"])

    def test_falls_back_to_stripped_original_for_empty_split(self):
        self.assertEqual(Extractor._sentences(""), [""])


class IsNoiseTests(unittest.TestCase):
    def test_pure_noise_and_speculation_are_noise(self):
        self.assertTrue(Extractor._is_noise("great chat everyone"))
        self.assertTrue(Extractor._is_noise("thanks everyone"))
        self.assertTrue(Extractor._is_noise("maybe someday we could improve"))
        self.assertTrue(Extractor._is_noise("someday it might work"))

    def test_commitment_signal_beats_noise_or_speculation(self):
        self.assertFalse(Extractor._is_noise("great chat but sarah will send memo"))
        self.assertFalse(Extractor._is_noise("maybe someday needs review"))

    def test_generic_text_without_signals_is_not_noise(self):
        self.assertFalse(Extractor._is_noise("random neutral sentence"))


class ExtractTitleTests(unittest.TestCase):
    def test_follow_up_branch(self):
        self.assertEqual(
            Extractor._extract_title("finance should follow up on customer"), "Finance follow-up"
        )

    def test_known_topic_short_circuits(self):
        for topic in KNOWN_TOPICS:
            self.assertEqual(
                Extractor._extract_title(f"we should send the {topic} tomorrow"),
                KNOWN_TOPICS[topic],
            )

    def test_send_pattern_falls_through_for_unknown_topic(self):
        self.assertEqual(Extractor._extract_title("nina will send widget by monday"), "Widget")

    def test_review_pattern(self):
        self.assertEqual(
            Extractor._extract_title("liam will review the widget by monday"), "Widget"
        )

    def test_owns_pattern(self):
        self.assertEqual(Extractor._extract_title("alex owns the widget now"), "Widget")

    def test_blocked_on_title_pattern(self):
        self.assertEqual(Extractor._extract_title("the widget is blocked on numbers"), "Widget")

    def test_risky_title_pattern(self):
        self.assertEqual(Extractor._extract_title("the widget is risky"), "Widget")

    def test_done_title_pattern(self):
        self.assertEqual(Extractor._extract_title("the widget is done"), "Widget")

    def test_need_pattern_returns_none_for_pronoun_only(self):
        self.assertIsNone(Extractor._extract_title("need this by monday"))

    def test_returns_none_for_untitled_text(self):
        self.assertIsNone(Extractor._extract_title("xylophone kaleidoscope"))


class ExtractOwnerTests(unittest.TestCase):
    def test_will_pattern(self):
        self.assertEqual(Extractor._extract_owner("Alice will send memo"), "Alice")

    def test_owns_pattern(self):
        self.assertEqual(Extractor._extract_owner("Alice owns the memo"), "Alice")

    def test_is_now_owner_pattern(self):
        self.assertEqual(Extractor._extract_owner("Alice is now owner of the memo"), "Alice")

    def test_requires_capitalized_first_letter(self):
        self.assertIsNone(Extractor._extract_owner("alice will send memo"))
        self.assertIsNone(Extractor._extract_owner("ALICE will send memo"))

    def test_none_when_no_owner_verb(self):
        self.assertIsNone(Extractor._extract_owner("Someone made a comment"))


class ExtractDeadlineTests(unittest.TestCase):
    def test_prefers_weekday(self):
        self.assertEqual(Extractor._extract_deadline("finish by Monday"), "Monday")
        self.assertEqual(Extractor._extract_deadline("finish by friday"), "Friday")

    def test_relative_by_clause(self):
        self.assertEqual(Extractor._extract_deadline("finish by today"), "today")
        self.assertEqual(Extractor._extract_deadline("finish by tomorrow"), "tomorrow")
        self.assertEqual(Extractor._extract_deadline("finish by end of week"), "end of week")
        self.assertEqual(Extractor._extract_deadline("finish by eow"), "eow")

    def test_none_without_deadline(self):
        self.assertIsNone(Extractor._extract_deadline("just a thought"))


class ExtractProjectsTests(unittest.TestCase):
    def test_captures_all_project_tokens(self):
        result = Extractor._extract_projects("Priya works on Project Atlas and Project Nova-1")
        self.assertEqual(result, ["Project Atlas", "Project Nova-1"])

    def test_none_when_no_project(self):
        self.assertEqual(Extractor._extract_projects("no project mentioned"), [])


class ExtractArtifactsTests(unittest.TestCase):
    def test_emits_for_known_artifact_terms(self):
        for title in ("Launch plan", "Board memo", "Data center report", "Security checklist"):
            self.assertEqual(Extractor._extract_artifacts(title), [title.lower()], msg=title)

    def test_none_for_titles_without_artifact_terms(self):
        self.assertEqual(Extractor._extract_artifacts("Widget"), [])


class ExtractBlockerTests(unittest.TestCase):
    def test_trims_tail_after_blocked_on(self):
        self.assertEqual(
            Extractor._extract_blocker("this is blocked on finance numbers"), "finance numbers"
        )

    def test_supports_underscore_and_hyphen(self):
        self.assertEqual(Extractor._extract_blocker("blocked on final_sign-off"), "final_sign-off")

    def test_none_without_blocker(self):
        self.assertIsNone(Extractor._extract_blocker("nothing blocking here"))


class ExtractReviewReasonTests(unittest.TestCase):
    def test_special_case_full_phrase(self):
        self.assertEqual(
            Extractor._extract_review_reason("it is risky and needs review today please"),
            "risky and needs review today",
        )

    def test_fallback_generic_keywords(self):
        self.assertEqual(Extractor._extract_review_reason("this is risky"), "risky")
        self.assertEqual(Extractor._extract_review_reason("needs review"), "needs review")
        self.assertEqual(Extractor._extract_review_reason("ambiguous case"), "ambiguous")
        self.assertEqual(
            Extractor._extract_review_reason("low confidence signal"), "low confidence"
        )

    def test_none_when_no_review_language(self):
        self.assertIsNone(Extractor._extract_review_reason("clear commitment"))


class ExtractDoneTests(unittest.TestCase):
    def test_all_completion_keywords(self):
        for word in ("done", "completed", "closed", "finished"):
            self.assertTrue(Extractor._extract_done(f"widget is {word}"), msg=word)

    def test_false_without_completion_keyword(self):
        self.assertFalse(Extractor._extract_done("widget is in progress"))


class ExtractDecisionsTests(unittest.TestCase):
    def test_captures_sentence_with_decided(self):
        self.assertEqual(
            Extractor._extract_decisions("Team decided to ship Friday"),
            ["Team decided to ship Friday"],
        )

    def test_captures_sentence_with_decision(self):
        self.assertEqual(
            Extractor._extract_decisions("Recorded the decision to ship"),
            ["Recorded the decision to ship"],
        )

    def test_empty_when_no_decision_language(self):
        self.assertEqual(Extractor._extract_decisions("just a normal sentence"), [])


class DedupeTests(unittest.TestCase):
    def test_case_insensitive_dedupe_preserves_first_occurrence(self):
        items = [
            WorkItem(title="Foo"),
            WorkItem(title="foo"),
            WorkItem(title="Bar"),
            WorkItem(title="FOO"),
        ]
        result = Extractor._dedupe(items)
        self.assertEqual([item.title for item in result], ["Foo", "Bar"])

    def test_empty_input_returns_empty(self):
        self.assertEqual(Extractor._dedupe([]), [])


class DayWordsTests(unittest.TestCase):
    def test_days_are_capitalized_seven_element_tuple(self):
        self.assertEqual(len(DAY_WORDS), 7)
        for day in DAY_WORDS:
            self.assertTrue(day[0].isupper())
            self.assertTrue(day[1:].islower())


class SlugifyTests(unittest.TestCase):
    def test_hyphenates_and_lowercases(self):
        self.assertEqual(WorkItem.slugify("Finance Follow-up"), "finance-follow-up")

    def test_returns_work_item_fallback_for_empty(self):
        self.assertEqual(WorkItem.slugify(""), "work-item")

    def test_returns_work_item_fallback_for_all_punctuation(self):
        self.assertEqual(WorkItem.slugify("!!!"), "work-item")

    def test_strips_leading_and_trailing_hyphens(self):
        self.assertEqual(WorkItem.slugify("---abc---"), "abc")

    def test_collapses_runs_of_non_alnum(self):
        self.assertEqual(WorkItem.slugify("a   b  c"), "a-b-c")


class AddSourceAndProvenanceTests(unittest.TestCase):
    def _fresh_item(self):
        return WorkItem(title="X")

    def test_add_source_is_idempotent_on_source_id(self):
        from chronograph.models import Source

        item = self._fresh_item()
        src = Source(source_id="s1", source_type="meeting", text="hello")
        item.add_source(src)
        item.add_source(src)
        self.assertEqual(item.source_ids, ["s1"])
        self.assertEqual(item.source_types, ["meeting"])

    def test_provenance_zips_ids_and_types(self):
        from chronograph.models import Source

        item = self._fresh_item()
        item.add_source(Source(source_id="s1", source_type="meeting", text="a"))
        item.add_source(Source(source_id="s2", source_type="slack", text="b"))
        self.assertEqual(item.provenance(), "s1 (meeting), s2 (slack)")


class SimilarTests(unittest.TestCase):
    def test_is_reflexive_on_nonempty(self):
        self.assertTrue(Chronograph._similar("Launch plan", "Launch plan"))

    def test_is_symmetric(self):
        left = "Launch plan review"
        right = "Launch plan"
        self.assertEqual(
            Chronograph._similar(left, right),
            Chronograph._similar(right, left),
        )

    def test_high_overlap_is_similar(self):
        self.assertTrue(Chronograph._similar("Launch plan", "Launch plan v2"))

    def test_low_overlap_is_not_similar(self):
        self.assertFalse(Chronograph._similar("Launch plan", "Security checklist"))

    def test_no_overlap_is_not_similar(self):
        self.assertFalse(Chronograph._similar("alpha beta", "gamma delta"))


class MergeFieldsTests(unittest.TestCase):
    def _graph(self):
        return Chronograph()

    def test_stronger_state_survives_active_merge(self):
        graph = self._graph()
        item = WorkItem(title="X", state="done")
        extracted = WorkItem(title="X", state="active")
        graph._merge_fields(item, extracted)
        self.assertEqual(item.state, "done")

    def test_active_upgraded_to_blocked_by_extracted(self):
        graph = self._graph()
        item = WorkItem(title="X", state="active")
        extracted = WorkItem(title="X", state="blocked")
        graph._merge_fields(item, extracted)
        self.assertEqual(item.state, "blocked")

    def test_review_reason_promotes_active_to_needs_review(self):
        graph = self._graph()
        item = WorkItem(title="X", state="active")
        extracted = WorkItem(title="X", state="active", review_reason="risky")
        graph._merge_fields(item, extracted)
        self.assertEqual(item.state, "needs_review")
        self.assertEqual(item.review_reason, "risky")

    def test_confidence_takes_minimum(self):
        graph = self._graph()
        item = WorkItem(title="X", confidence=1.0)
        extracted = WorkItem(title="X", confidence=0.3)
        graph._merge_fields(item, extracted)
        self.assertAlmostEqual(item.confidence, 0.3)

    def test_lists_merge_without_duplicates(self):
        graph = self._graph()
        item = WorkItem(title="X", projects=["Project Atlas"], artifacts=["memo"])
        extracted = WorkItem(
            title="X", projects=["Project Atlas", "Project Nova"], artifacts=["memo", "plan"]
        )
        graph._merge_fields(item, extracted)
        self.assertEqual(item.projects, ["Project Atlas", "Project Nova"])
        self.assertEqual(item.artifacts, ["memo", "plan"])


if __name__ == "__main__":
    unittest.main()
