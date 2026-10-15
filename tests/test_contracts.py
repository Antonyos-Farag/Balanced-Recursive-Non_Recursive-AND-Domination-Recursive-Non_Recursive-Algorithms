"""The review: which programs agree, which disagree, and exactly how.

This file is the *comparison*, not the bug list.  For every disagreement it
asserts the disagreement itself, so a reader can run one command and see the
whole picture instead of trusting a paragraph of prose.

The archived programs are wrapped by ``algorithms.original.adapters``, which
converts their answers into the shared contract (a ``(length, sorted names)``
pair, or a ``Dominator``/``None``) **without** repairing their behaviour.
"""

from __future__ import annotations

import unittest

from algorithms import balanced, dominator
from algorithms.dominator.result import Dominator
from algorithms.original import adapters
from algorithms.original import dominator_iterative as legacy_loop
from algorithms.original import dominator_recursive as legacy_dc

ALL_DOMINATOR = dict(dominator.IMPLEMENTATIONS, **adapters.LEGACY_DOMINATOR)


class TestBalancedContract(unittest.TestCase):
    """The repaired implementations agree; the archived ones do not."""

    def test_the_repaired_implementations_agree(self):
        for text in ["aabb", "aabbb", "aabbc", "ababab", "abcabc", "aaabbb", ""]:
            expected = balanced.reference(text)
            for name, function in balanced.IMPLEMENTATIONS.items():
                with self.subTest(text=text, implementation=name):
                    self.assertEqual(function(text), expected)

    def test_the_recursive_submission_agrees_with_the_contract(self):
        """It is correct -- see tests/test_original_characterization.py."""
        for text in ["aabb", "aabbb", "aabbc", "ababab", "abcabc", "aaabbb", ""]:
            with self.subTest(text=text):
                self.assertEqual(adapters.legacy_recursive(text), balanced.reference(text))

    def test_the_loop_submission_disagrees_whenever_a_scan_dies_early(self):
        """Bug B1, at the contract level: four inputs, four wrong answers."""
        wrong = {
            "aabbb": (0, []),  # the right answer is (4, ['aabb'])
            "aabbc": (2, ["bc"]),  # the right answer is (4, ['aabb'])
            "abcabc": (2, ["bc"]),  # the right answer is (2, ['ab','bc','ca'])
            "aabbaa": (4, ["bbaa"]),  # the right answer is (4, ['aabb','abba','bbaa'])
        }
        for text, expected in wrong.items():
            with self.subTest(text=text):
                self.assertEqual(adapters.legacy_iterative(text), expected)
                self.assertNotEqual(adapters.legacy_iterative(text), balanced.reference(text))

    def test_it_is_right_when_every_scan_runs_to_the_end(self):
        """The bug is silent, so it hides behind examples that happen to work."""
        for text in ["aabb", "abab", "ababab", "aaabbb"]:
            with self.subTest(text=text):
                self.assertEqual(adapters.legacy_iterative(text), balanced.reference(text))

    def test_the_two_submissions_disagree_with_each_other(self):
        """Same problem, same author, two programs, two different answers."""
        for text in ["aabbb", "aabbc", "abcabc", "aabbaa"]:
            with self.subTest(text=text):
                self.assertNotEqual(
                    adapters.legacy_iterative(text),
                    adapters.legacy_recursive(text),
                )

    def test_the_disagreement_is_never_in_the_length_alone(self):
        """A tie-hiding bug: same length, one answer instead of three."""
        self.assertEqual(adapters.legacy_iterative("abcabc")[0], balanced.reference("abcabc")[0])
        self.assertEqual(adapters.legacy_iterative("abcabc")[1], ["bc"])
        self.assertEqual(balanced.reference("abcabc")[1], ["ab", "bc", "ca"])


class TestBalancedInputPolicy(unittest.TestCase):
    """Two programs, two policies, one of which is not a policy at all."""

    def test_uppercase(self):
        # The loop version refuses the input out loud and answers 0.
        self.assertEqual(adapters.legacy_iterative("AAbb"), (0, []))
        # The recursive version quietly lower-cases it and answers correctly.
        self.assertEqual(adapters.legacy_recursive("AAbb"), (4, ["aabb"]))
        # The repaired package folds case, like the recursive one, and says so.
        self.assertEqual(balanced.reference("AAbb"), (4, ["aabb"]))

    def test_non_letters_cross_three_different_policies(self):
        # 1. The loop version rejects the input before doing anything.
        self.assertEqual(adapters.legacy_iterative("ab1cdef"), (0, []))
        # 2. The recursive version treats non-letters as a wall and keeps going.
        #    The answer happens to be right anyway (the characterization tests
        #    prove it), but the caller is never told.
        self.assertEqual(adapters.legacy_recursive("ab1cdef"), (2, ["ab", "cd", "de", "ef"]))
        # 3. The repaired package raises, so a typo cannot become a wrong answer.
        with self.assertRaises(ValueError):
            balanced.reference("ab1cdef")

    def test_non_ascii_crashes_the_recursive_submission(self):
        with self.assertRaises(IndexError):
            adapters.legacy_recursive("caf\u00e9")
        # The repaired version raises something a caller can act on.
        with self.assertRaises(ValueError):
            balanced.recursive("caf\u00e9")


class TestDominatorContract(unittest.TestCase):
    """-1, [] and None: three ways of saying nothing at all."""

    def test_no_dominator_is_expressed_three_ways(self):
        a = [1, 2, 3, 4]
        self.assertEqual(legacy_loop.dominator(a), -1)
        self.assertEqual(legacy_dc.find_dominator_indices(a), [])
        self.assertIsNone(dominator.boyer_moore(a))

    def test_the_adapters_hide_the_shape_not_the_behaviour(self):
        self.assertIsNone(adapters.legacy_dominator([1, 2, 3, 4]))
        self.assertIsNone(adapters.legacy_divide_and_conquer([1, 2, 3, 4]))

    def test_agreement_on_integer_arrays(self):
        cases = [
            [3, 1, 3, 2, 3, 4, 3, 3],
            [2],
            [],
            [1, 1, 1, 2],
            [1, 1, 2, 2],
            [0, 0, 0, 0, 1],
        ]
        for a in cases:
            expected = dominator.boyer_moore(a)
            for name, function in ALL_DOMINATOR.items():
                with self.subTest(a=a, implementation=name):
                    self.assertEqual(function(a), expected)

    def test_the_recursive_submission_cannot_see_a_none_dominator(self):
        """Bug B12, at the contract level."""
        a = [None, None, 1]
        self.assertEqual(dominator.boyer_moore(a), Dominator(None, (0, 1)))
        self.assertIsNone(adapters.legacy_divide_and_conquer(a))

    def test_the_two_submissions_do_not_even_agree_on_multiplicity(self):
        """One returns *a* thing, the other returns *all* the things."""
        a = [3, 1, 3, 2, 3, 4, 3, 3]
        self.assertEqual(legacy_loop.dominator(a), [0, 2, 4, 6, 7])
        self.assertEqual(legacy_dc.find_dominator_indices(a), [0, 2, 4, 6, 7])


class TestCrossPackageSanity(unittest.TestCase):
    def test_registries_cover_every_public_implementation(self):
        self.assertEqual(
            set(balanced.IMPLEMENTATIONS),
            {
                "reference",
                "brute_force",
                "brute_force_incremental",
                "round_trip",
                "recursive",
                "recursive_shared_freq",
                "pair_scan",
                "pair_scan_two_pass",
            },
        )
        self.assertEqual(
            set(dominator.IMPLEMENTATIONS),
            {"boyer_moore", "divide_and_conquer", "index_cache", "sort_and_pick_middle"},
        )

    def test_legacy_registries(self):
        self.assertEqual(set(adapters.LEGACY_BALANCED), {"legacy_iterative", "legacy_recursive"})
        self.assertEqual(
            set(adapters.LEGACY_DOMINATOR),
            {"legacy_dominator", "legacy_divide_and_conquer"},
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
