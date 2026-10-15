"""The definition of "balanced", the input policy, and the small helpers."""

from __future__ import annotations

import random
import unittest

from algorithms.balanced.core import (
    ALPHABET_SIZE,
    BestTracker,
    counts_of,
    equal_pair,
    freq_summary,
    is_balanced,
    legacy_equal_pair,
    normalize,
)


class TestIsBalanced(unittest.TestCase):
    """`is_balanced` is the definition; if it is wrong, nothing else matters."""

    def test_balanced_examples(self):
        for text in ["ab", "ba", "aabb", "abab", "abba", "baab", "bbaa", "aaabbb", "abcabc"[0:2]]:
            with self.subTest(text=text):
                self.assertTrue(is_balanced(text))

    def test_not_balanced_examples(self):
        cases = {
            "": "nothing at all",
            "a": "one character",
            "aaaa": "only one distinct character",
            "aaabb": "counts differ",
            "aabbb": "counts differ",
            "abc": "three distinct characters",
            "aabbc": "three distinct characters",
        }
        for text, why in cases.items():
            with self.subTest(text=text, why=why):
                self.assertFalse(is_balanced(text))

    def test_counts_of(self):
        self.assertEqual(counts_of("aabbbc"), {"a": 2, "b": 3, "c": 1})

    def test_alphabet_size_is_26(self):
        self.assertEqual(ALPHABET_SIZE, 26)
        self.assertTrue(equal_pair([1, 1] + [0] * 24))
        # All 26 letters once each is *not* a pair, however big the table is.
        self.assertFalse(equal_pair([1] * 26))


class TestEqualPair(unittest.TestCase):
    """The hot inner test -- and the weaker one the submission used."""

    def test_the_repaired_version_rejects_a_third_letter(self):
        self.assertFalse(equal_pair([2, 2, 1] + [0] * 23))
        self.assertFalse(equal_pair([1, 1, 1] + [0] * 23))

    def test_the_repaired_version_accepts_two_equal_counts(self):
        self.assertTrue(equal_pair([3, 0, 0, 3] + [0] * 22))
        self.assertTrue(equal_pair([0] * 20 + [7, 0, 0, 0, 0, 7]))

    def test_rejects_zero_or_one_letters(self):
        self.assertFalse(equal_pair([5] + [0] * 25))
        self.assertFalse(equal_pair([0] * 26))

    def test_the_submitted_version_is_weaker(self):
        """Documents bug B1b: the archived test ignores a third letter."""
        table = [2, 2, 1] + [0] * 23
        self.assertTrue(legacy_equal_pair(table))  # three letters, all "fine"
        self.assertFalse(equal_pair(table))  # the repaired version disagrees

    def test_agreement_on_legal_two_letter_tables(self):
        for first in range(6):
            for second in range(6):
                table = [0] * 26
                table[0], table[1] = first, second
                if first and second and first == second:
                    self.assertTrue(equal_pair(table))
                    self.assertTrue(legacy_equal_pair(table))
                else:
                    self.assertFalse(equal_pair(table))

    def test_freq_summary(self):
        self.assertEqual(freq_summary([2, 0, 1] + [0] * 23), "a:2 c:1")
        self.assertEqual(freq_summary([0] * 26), "-")


class TestTheTwoBalanceTestsAgree(unittest.TestCase):
    """``equal_pair`` and "the largest count is half the window" must agree.

    ``brute_force_incremental`` replaces the 26-slot walk with
    ``2 * max_count == window length``. That is only sound if the two criteria
    are the same statement for every frequency table a window can produce, so
    this test walks the *tables* rather than the strings: an edit that broke both
    sides identically would slip past the exhaustive string tests, and this
    catches it.
    """

    def test_tables_agree_on_every_reachable_frequency_table(self):
        rng = random.Random(20240519)
        for _ in range(2000):
            text = "".join(rng.choice("abcd") for _ in range(rng.randint(1, 12)))
            freq = [0] * 26
            distinct = 0
            max_count = 0
            for end, ch in enumerate(text):
                index = ord(ch) - ord("a")
                if freq[index] == 0:
                    distinct += 1
                freq[index] += 1
                max_count = max(max_count, freq[index])
                with self.subTest(window=text[: end + 1]):
                    self.assertEqual(
                        distinct == 2 and equal_pair(freq),
                        distinct == 2 and 2 * max_count == end + 1,
                    )


class TestNormalize(unittest.TestCase):
    """One input policy for the whole package."""

    def test_lowercase_passthrough(self):
        self.assertEqual(normalize("abcxyz"), "abcxyz")

    def test_case_is_folded_by_default(self):
        self.assertEqual(normalize("AaBb"), "aabb")

    def test_casefold_off_rejects_uppercase(self):
        with self.assertRaises(ValueError) as caught:
            normalize("AaBb", casefold=False)
        self.assertIn("'A'", str(caught.exception))
        self.assertIn("index 0", str(caught.exception))

    def test_none_is_the_empty_string(self):
        self.assertEqual(normalize(None), "")

    def test_rejects_digits_and_punctuation(self):
        for bad, position in [("ab1c", 2), ("a b", 1), ("ab-c", 2), ("ab\n", 2), ("ab!", 2)]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError) as caught:
                    normalize(bad)
                self.assertIn(f"index {position}", str(caught.exception))

    def test_rejects_non_ascii_letters(self):
        # The archived recursive program crashed on this input (bug B3).
        with self.assertRaises(ValueError):
            normalize("caf\u00e9")

    def test_rejects_non_strings(self):
        with self.assertRaises(TypeError):
            normalize(1234)  # type: ignore[arg-type]


class TestBestTracker(unittest.TestCase):
    def test_keeps_only_the_longest(self):
        tracker = BestTracker()
        tracker.consider("ab")
        tracker.consider("abcd"[0:2])
        self.assertEqual(tracker.result(), (2, ["ab"]))
        tracker.consider("aabb")
        self.assertEqual(tracker.result(), (4, ["aabb"]))

    def test_collects_ties_without_duplicates(self):
        tracker = BestTracker()
        for candidate in ["ab", "ba", "ab"]:
            tracker.consider(candidate)
        self.assertEqual(tracker.result(), (2, ["ab", "ba"]))

    def test_ignores_the_empty_string(self):
        tracker = BestTracker()
        tracker.consider("")
        self.assertEqual(tracker.result(), (0, []))

    def test_merge_promotes_the_longer_tracker(self):
        small, big = BestTracker(), BestTracker()
        small.consider("ab")
        big.consider("aabb")
        small.merge(big)
        self.assertEqual(small.result(), (4, ["aabb"]))

    def test_merge_keeps_the_longer_one(self):
        small, big = BestTracker(), BestTracker()
        small.consider("aabb")
        big.consider("ab")
        small.merge(big)
        self.assertEqual(small.result(), (4, ["aabb"]))

    def test_merge_collects_ties(self):
        left, right = BestTracker(), BestTracker()
        left.consider("aabb")
        right.consider("bbaa")
        left.merge(right)
        self.assertEqual(left.result(), (4, ["aabb", "bbaa"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
