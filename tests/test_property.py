"""Randomized property-based tests using stdlib `random` with a deterministic seed.

No third-party dependency added — this stays inside the repo's zero-dep runtime
posture. Each property function seeds its own RNG so failures are reproducible.
"""

import random
import string
import unittest

from chronograph import Chronograph
from chronograph.extractor import Extractor
from chronograph.models import WorkItem

TITLE_ALPHABET = string.ascii_letters + string.digits + " -_.,'!?"


class SlugifyPropertyTests(unittest.TestCase):
    def test_slugify_output_shape(self):
        rng = random.Random(0)
        for _ in range(300):
            length = rng.randint(0, 40)
            s = "".join(rng.choice(TITLE_ALPHABET + "  ") for _ in range(length))
            slug = WorkItem.slugify(s)
            self.assertGreater(len(slug), 0, msg=f"empty slug for {s!r}")
            self.assertRegex(slug, r"^[a-z0-9-]+$", msg=f"bad chars for {s!r}: {slug!r}")
            self.assertFalse(slug.startswith("-"), msg=f"leading hyphen for {s!r}: {slug!r}")
            self.assertFalse(slug.endswith("-"), msg=f"trailing hyphen for {s!r}: {slug!r}")


class SentencesPropertyTests(unittest.TestCase):
    def test_sentences_always_returns_at_least_one_stripped_element(self):
        rng = random.Random(1)
        fragments = [
            "hi",
            "hello world",
            "bye",
            "no signals",
            "will send",
            "owns",
            "review",
            "great chat",
        ]
        for _ in range(200):
            n = rng.randint(1, 5)
            sep_pool = [". ", "! ", "? ", ".  "]
            text = ""
            for i in range(n):
                text += rng.choice(fragments)
                if i < n - 1:
                    text += rng.choice(sep_pool)
            parts = Extractor._sentences(text)
            self.assertGreaterEqual(len(parts), 1)
            for part in parts:
                self.assertEqual(part, part.strip(), msg=f"unstripped part in {text!r}")


class DedupePropertyTests(unittest.TestCase):
    def test_dedupe_output_is_case_insensitively_unique_and_shorter(self):
        rng = random.Random(2)
        for _ in range(200):
            n = rng.randint(0, 20)
            titles = [rng.choice(["foo", "Foo", "bar", "BAR", "baz", "Qux"]) for _ in range(n)]
            items = [WorkItem(title=t) for t in titles]
            out = Extractor._dedupe(items)
            self.assertLessEqual(len(out), len(items))
            lowered = [i.title.lower() for i in out]
            self.assertEqual(len(set(lowered)), len(lowered))

            seen = set()
            expected_first = []
            for title in titles:
                key = title.lower()
                if key not in seen:
                    seen.add(key)
                    expected_first.append(title)
            self.assertEqual([o.title for o in out], expected_first)


class SimilarPropertyTests(unittest.TestCase):
    def test_similar_is_reflexive_on_non_empty_strings(self):
        rng = random.Random(3)
        pool = ["alpha", "beta", "gamma", "delta", "eps"]
        for _ in range(200):
            k = rng.randint(1, 4)
            s = " ".join(rng.sample(pool, k=min(k, len(pool))))
            self.assertTrue(Chronograph._similar(s, s), msg=f"not reflexive on {s!r}")

    def test_similar_is_symmetric(self):
        rng = random.Random(4)
        pool = ["alpha", "beta", "gamma", "delta", "eps", "zeta", "eta", "theta"]
        for _ in range(300):
            a = " ".join(rng.sample(pool, k=rng.randint(1, 4)))
            b = " ".join(rng.sample(pool, k=rng.randint(1, 4)))
            self.assertEqual(
                Chronograph._similar(a, b),
                Chronograph._similar(b, a),
                msg=f"asymmetric on {a!r},{b!r}",
            )


class ExtractIdempotencePropertyTests(unittest.TestCase):
    def test_extract_is_deterministic_and_idempotent(self):
        rng = random.Random(5)
        templates = [
            "{owner} will send {topic} by {day}",
            "{topic} is blocked on {blocker}",
            "{topic} is risky and needs review today",
            "{topic} is done",
            "{owner} owns {topic}",
            "Great chat everyone. {owner} will send {topic} by {day}",
        ]
        owners = ["Alice", "Bob", "Carol", "Dan"]
        topics = ["widget", "spec", "report", "quote", "response"]
        days = ["Monday", "Tuesday", "Wednesday", "Friday"]
        blockers = ["numbers", "signoff", "final_review"]

        extractor = Extractor()
        for _ in range(150):
            text = rng.choice(templates).format(
                owner=rng.choice(owners),
                topic=rng.choice(topics),
                day=rng.choice(days),
                blocker=rng.choice(blockers),
            )
            first = extractor.extract("s1", "meeting", text)
            second = extractor.extract("s1", "meeting", text)
            first_shape = [
                (i.title, i.owner, i.deadline, i.state, i.blocker, i.review_reason) for i in first
            ]
            second_shape = [
                (i.title, i.owner, i.deadline, i.state, i.blocker, i.review_reason) for i in second
            ]
            self.assertEqual(
                first_shape, second_shape, msg=f"extract not idempotent for text={text!r}"
            )


class MergeFieldsPropertyTests(unittest.TestCase):
    def test_active_extracted_state_never_downgrades_stronger_state(self):
        rng = random.Random(6)
        stronger = ["blocked", "needs_review", "done"]
        for _ in range(100):
            current = rng.choice(stronger)
            graph = Chronograph()
            item = WorkItem(title="X", state=current)
            extracted = WorkItem(title="X", state="active")
            graph._merge_fields(item, extracted)
            self.assertEqual(item.state, current, msg=f"active downgraded {current}")

    def test_confidence_after_merge_is_minimum(self):
        rng = random.Random(7)
        for _ in range(100):
            c1 = rng.random()
            c2 = rng.random()
            graph = Chronograph()
            item = WorkItem(title="X", confidence=c1)
            extracted = WorkItem(title="X", confidence=c2)
            graph._merge_fields(item, extracted)
            self.assertAlmostEqual(item.confidence, min(c1, c2))


class BoundaryScriptContractTests(unittest.TestCase):
    """The DAY_WORDS canonical location contract: extractor is the single owner."""

    def test_day_words_import_from_extractor_matches_engine_usage(self):
        from chronograph import engine as engine_module
        from chronograph.extractor import DAY_WORDS

        self.assertIs(engine_module.DAY_WORDS, DAY_WORDS)


if __name__ == "__main__":
    unittest.main()
