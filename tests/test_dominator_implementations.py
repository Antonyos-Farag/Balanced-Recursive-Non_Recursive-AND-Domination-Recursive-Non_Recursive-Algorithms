"""The four dominator strategies, against a definition-level oracle.

The oracle is written straight from the definition -- "count every value, keep
the one that appears more than half the time" -- so it is slow and obvious.  It
also avoids the two traps that make dominator code go wrong:

* it never trusts a candidate without counting it, and
* it distinguishes "no dominator" (``None``) from "the dominator's value is
  ``None``" (a ``Dominator`` whose ``value`` is ``None``).
"""

from __future__ import annotations

import itertools
import random
import unittest

from algorithms import dominator
from algorithms.dominator import IMPLEMENTATIONS
from algorithms.dominator.result import Dominator


def oracle(a):
    """The definition, applied literally."""
    n = len(a)
    for value in set_of_values(a):
        indices = tuple(i for i in range(n) if a[i] == value)
        if len(indices) > n // 2:
            return Dominator(value, indices)
    return None


def set_of_values(a):
    """Distinct values, tolerant of unhashable entries (lists, dicts...)."""
    values = []
    for item in a:
        if not any(item == seen for seen in values):
            values.append(item)
    return values


class TestAgainstOracleExhaustive(unittest.TestCase):
    def test_all_arrays_over_three_values_up_to_length_7(self):
        for length in range(0, 8):
            for values in itertools.product([0, 1, 2], repeat=length):
                a = list(values)
                expected = oracle(a)
                for name, function in IMPLEMENTATIONS.items():
                    with self.subTest(a=a, implementation=name):
                        if name == "sort_and_pick_middle":
                            continue  # needs comparable values; covered below
                        self.assertEqual(function(a), expected)

    def test_all_arrays_over_two_values_up_to_length_10(self):
        for length in range(0, 11):
            for values in itertools.product([0, 1], repeat=length):
                a = list(values)
                expected = oracle(a)
                for name, function in IMPLEMENTATIONS.items():
                    with self.subTest(a=a, implementation=name):
                        if name == "sort_and_pick_middle":
                            continue
                        self.assertEqual(function(a), expected)


class TestSortAndPickMiddle(unittest.TestCase):
    """The sorting strategy, on inputs whose values can be ordered."""

    def test_exhaustive_on_comparable_values(self):
        for length in range(0, 8):
            for values in itertools.product([0, 1, 2], repeat=length):
                a = list(values)
                with self.subTest(a=a):
                    self.assertEqual(dominator.sort_and_pick_middle(a), oracle(a))

    def test_middle_element_lemma_holds_for_every_dominator(self):
        """If x dominates, x *is* the middle of the sorted array."""
        rng = random.Random(11)
        for _ in range(500):
            n = rng.randint(1, 40)
            a = [rng.randint(0, 3) for _ in range(n)]
            expected = oracle(a)
            if expected is not None:
                self.assertEqual(sorted(a)[n // 2], expected.value)

    def test_it_reports_the_precondition_it_cannot_meet(self):
        # None cannot be compared with None; the other three implementations
        # have no such requirement, which is a real trade-off worth a test.
        with self.assertRaises(TypeError):
            dominator.sort_and_pick_middle([None, None, 1])


class TestNoneAsAValue(unittest.TestCase):
    """The bug the archived recursive program has (B12) must not come back."""

    def test_none_can_dominate(self):
        a = [None, None, 1]
        expected = Dominator(None, (0, 1))
        self.assertEqual(dominator.boyer_moore(a), expected)
        self.assertEqual(dominator.divide_and_conquer(a), expected)
        self.assertEqual(dominator.index_cache(a), expected)
        self.assertIsNotNone(dominator.boyer_moore(a))

    def test_no_dominator_is_none_not_a_fake_result(self):
        self.assertIsNone(dominator.boyer_moore([1, 2, 3, 4]))
        self.assertIsNone(dominator.divide_and_conquer([1, 2, 3, 4]))

    def test_unhashable_values_work_where_the_algorithm_allows_it(self):
        a = [[1], [1], [2]]
        self.assertEqual(dominator.boyer_moore(a), Dominator([1], (0, 1)))
        self.assertEqual(dominator.divide_and_conquer(a), Dominator([1], (0, 1)))
        with self.assertRaises(TypeError):
            dominator.index_cache(a)  # lists are not hashable


class TestKnownAnswers(unittest.TestCase):
    def test_the_running_example(self):
        a = [3, 1, 3, 2, 3, 4, 3, 3]
        expected = Dominator(3, (0, 2, 4, 6, 7))
        for name, function in IMPLEMENTATIONS.items():
            with self.subTest(implementation=name):
                self.assertEqual(function(a), expected)

    def test_strictly_more_than_half(self):
        """Exactly half is not a dominator -- the comparison is > not >=."""
        self.assertIsNone(dominator.boyer_moore([1, 1, 2, 2]))
        self.assertEqual(dominator.boyer_moore([1, 1, 1, 2]), Dominator(1, (0, 1, 2)))

    def test_single_element(self):
        self.assertEqual(dominator.boyer_moore([7]), Dominator(7, (0,)))

    def test_empty_array(self):
        for name, function in IMPLEMENTATIONS.items():
            with self.subTest(implementation=name):
                self.assertIsNone(function([]))

    def test_the_submitted_example_with_the_wrong_comment(self):
        """The archived demo printed [2] for A=[2] next to a comment about 3s.

        The answer for ``[2]`` is index ``0``; the comment in the submission
        promised ``[0, 2, 4, 6, 7]`` for a totally different array.  Bug B14.
        """
        self.assertEqual(dominator.boyer_moore([2]), Dominator(2, (0,)))

    def test_any_index_variant(self):
        self.assertEqual(dominator.any_index([3, 1, 3, 2, 3, 4, 3, 3]), 0)
        self.assertEqual(dominator.any_index([1, 2, 3]), -1)
        self.assertEqual(dominator.any_index([]), -1)


class TestVoteMechanics(unittest.TestCase):
    def test_the_candidate_alone_can_be_wrong(self):
        """Boyer-Moore without verification is a bug, not an optimisation."""
        a = [1, 2, 3]
        self.assertEqual(dominator.candidate_or_none(a), 3)
        self.assertIsNone(dominator.boyer_moore(a))

    def test_walk_reports_elect_support_cancel(self):
        self.assertEqual(
            dominator.vote_steps([1, 1, 2, 3]),
            # 1 keeps the seat through a support and a cancel; 3 then cancels
            # the last survivor, so nothing is left standing -- and [1,1,2,3]
            # really does have no dominator (1 occurs twice, not > 4/2).
            [(0, 1, "elect", 1, 1), (1, 1, "support", 1, 2), (2, 2, "cancel", 1, 1), (3, 3, "cancel", 1, 0)],
        )

    def test_walk_is_empty_for_an_empty_array(self):
        self.assertEqual(dominator.walk_votes([]), [])

    def test_count_never_stays_negative(self):
        rng = random.Random(3)
        for _ in range(200):
            a = [rng.randint(0, 2) for _ in range(rng.randint(0, 30))]
            for step in dominator.walk_votes(a):
                self.assertGreaterEqual(step.count, 0)


class TestDominatorObject(unittest.TestCase):
    def test_count_and_percentage(self):
        d = Dominator(3, (0, 2, 4, 6, 7))
        self.assertEqual(len(d), 5)
        self.assertEqual(d.count, 5)
        self.assertEqual(d.percentage(8), 62.5)

    def test_percentage_needs_a_positive_total(self):
        with self.assertRaises(ValueError):
            Dominator(1, (0,)).percentage(0)

    def test_it_is_iterable_and_hashable(self):
        d = Dominator(3, (0, 2))
        self.assertEqual(list(d), [0, 2])
        self.assertEqual({d: "yes"}[Dominator(3, (0, 2))], "yes")

    def test_structural_equality_is_not_value_equality(self):
        # Dominator(None, ()) is not the same thing as None: only the former is
        # an answer, and that distinction is the whole point of the type.
        self.assertNotEqual(Dominator(None, ()), None)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
