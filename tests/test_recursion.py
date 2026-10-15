"""Recursion depth is a real, measurable resource.  This file measures it.

Three things are checked here:

1. the archived recursive program dies on long input (bug B4) and the *reason*
   is depth, not size -- a 4,000-character string is trivial for the loop
   version, and a 996-character string is already fatal for the recursion;
2. the repaired recursion has (almost exactly) the same depth profile, because
   the depth belongs to the algorithm, not to the bug;
3. :func:`algorithms.support.run_deep` is the supported way to lift the limit,
   and it works: the same function, the same input, no crash.
"""

from __future__ import annotations

import unittest

from algorithms import balanced
from algorithms.balanced.recursion import recursive_depth
from algorithms.original import balanced_recursive as legacy_recursive
from algorithms.support import run_deep

LIMIT = 1000  # CPython's default; tests stay well clear of the exact boundary


class TestDepthProfile(unittest.TestCase):
    def test_depth_grows_with_the_window_not_with_the_string(self):
        # "ab" repeated never shows a third letter, so every scan runs to the
        # end of the string: depth ~ window length.
        self.assertEqual(recursive_depth("ab" * 10), 21)
        self.assertEqual(recursive_depth("ab" * 20), 41)

    def test_a_third_letter_shortens_the_window_and_the_depth(self):
        # "abcabc": every scan dies as soon as the third letter appears, so the
        # longest chain is start=0 -> end=2, i.e. three frames.
        self.assertEqual(recursive_depth("abcabc"), 3)
        # "ababab": nothing ever dies, so the chain runs to the end of the
        # 6-character string and then stops on the "end == len(text)" call,
        # which is why the depth is len(text) + 1 and not len(text).
        self.assertEqual(recursive_depth("ababab"), 7)

    def test_short_strings_are_shallow(self):
        self.assertEqual(recursive_depth(""), 0)
        self.assertEqual(recursive_depth("a"), 2)  # end=0, then the no-op end=1
        self.assertEqual(recursive_depth("aabb"), 5)  # end=0..3, then end=4


class TestTheLimitIsReal(unittest.TestCase):
    def test_the_archived_program_dies_on_long_input(self):
        with self.assertRaises(RecursionError):
            legacy_recursive.LBS("a" * 2000)

    def test_the_loop_version_does_not_care_about_the_same_shape(self):
        # Three times the recursion limit, and the loop version does not even
        # notice.  (It is slow, though -- all those identical letters never
        # trigger the "third letter" shortcut.  See docs/05-complexity-lab.md.)
        self.assertEqual(balanced.brute_force("a" * 2000), (0, []))

    def test_the_repaired_recursion_dies_at_about_the_same_size(self):
        # This is not the bug -- it is the shape of the algorithm.  Fixing the
        # balance check does not buy a single extra character of depth.
        with self.assertRaises(RecursionError):
            balanced.recursive("a" * 2000)
        self.assertEqual(balanced.recursive("a" * 900), (0, []))

    def test_the_shared_frequency_version_has_the_same_depth(self):
        with self.assertRaises(RecursionError):
            balanced.recursive_shared_freq("a" * 2000)

    def test_depth_is_what_breaks_it_not_the_string(self):
        """One extra character is the whole difference at the boundary."""
        # Well inside the limit:
        balanced.recursive("a" * 900)
        # Well outside it:
        with self.assertRaises(RecursionError):
            balanced.recursive("a" * 1100)


class TestTheWayOut(unittest.TestCase):
    def test_run_deep_lifts_the_limit_and_grows_the_stack(self):
        # 1,500 characters is 50% beyond the default limit.  (The recursion is
        # quadratic in calls, so this test stays deliberately small; the
        # benchmark in tools/bench.py is where the big numbers live.)
        result = run_deep(balanced.recursive, "a" * 1500)
        self.assertEqual(result, (0, []))

    def test_recursive_deep_agrees_with_the_fast_algorithm(self):
        # The recursion is now exercised on an input the reference oracle could
        # never finish, so the cross-check uses the pair scan (itself verified
        # exhaustively against the oracle in test_balanced_implementations.py).
        text = "aabbb" * 300  # 1,500 characters: past the limit, still quick
        self.assertEqual(balanced.recursive_deep(text), balanced.pair_scan(text))

    def test_run_deep_propagates_exceptions(self):
        def boom():
            raise ValueError("from the bottom of the stack")

        with self.assertRaises(ValueError):
            run_deep(boom)

    def test_run_deep_restores_the_recursion_limit(self):
        import sys

        before = sys.getrecursionlimit()
        run_deep(balanced.recursive, "a" * 1200)
        self.assertEqual(sys.getrecursionlimit(), before)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
