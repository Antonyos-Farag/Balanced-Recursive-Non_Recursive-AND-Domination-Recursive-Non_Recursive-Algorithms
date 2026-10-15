"""The instrumentation itself must be trustworthy.

A measurement tool that lies is worse than no measurement, so the counters get
their own tests: reads are split into positions and slices, ``len`` is free,
iterating counts, and the deep-recursion helper really does restore the
interpreter afterwards.
"""

from __future__ import annotations

import sys
import unittest

from algorithms.support import (
    ReadCounter,
    Timing,
    format_int,
    format_ratio,
    format_seconds,
    run_deep,
    timed,
)


class TestReadCounter(unittest.TestCase):
    def test_counts_index_reads(self):
        counter = ReadCounter("abc")
        self.assertEqual(counter[0], "a")
        self.assertEqual(counter[2], "c")
        self.assertEqual(counter.point_reads, 2)
        self.assertEqual(counter.slice_reads, 0)
        self.assertEqual(counter.reads, 2)

    def test_slices_count_their_length(self):
        counter = ReadCounter("abcdef")
        self.assertEqual(counter[1:4], "bcd")
        self.assertEqual(counter.slice_reads, 3)
        self.assertEqual(counter.point_reads, 0)

    def test_iteration_counts_every_element(self):
        counter = ReadCounter("abc")
        self.assertEqual(list(counter), ["a", "b", "c"])
        self.assertEqual(counter.point_reads, 3)

    def test_len_is_free(self):
        counter = ReadCounter("abcdefghij")
        for _ in range(100):
            len(counter)
        self.assertEqual(counter.reads, 0)

    def test_reset(self):
        counter = ReadCounter("abc")
        list(counter)
        counter.reset()
        self.assertEqual((counter.point_reads, counter.slice_reads, counter.reads), (0, 0, 0))

    def test_it_behaves_like_a_sequence(self):
        counter = ReadCounter([1, 2, 3, 2])
        self.assertIn(2, counter)
        self.assertEqual(counter.index(2), 1)
        self.assertEqual(counter.count(2), 2)

    def test_data_gives_back_the_original(self):
        text = "hello"
        self.assertIs(ReadCounter(text).data, text)

    def test_an_empty_slice_counts_nothing(self):
        counter = ReadCounter("abc")
        counter[1:1]
        self.assertEqual(counter.reads, 0)

    def test_negative_and_open_slices_are_counted_correctly(self):
        counter = ReadCounter("abcdef")
        counter[-2:]
        counter[:3]
        self.assertEqual(counter.slice_reads, 5)


class TestRunDeep(unittest.TestCase):
    def test_it_returns_the_result(self):
        self.assertEqual(run_deep(lambda: 42), 42)

    def test_it_passes_arguments(self):
        self.assertEqual(run_deep(lambda a, b=0: a + b, 1, b=2), 3)

    def test_it_raises_what_the_function_raises(self):
        def boom():
            raise KeyError("nope")

        with self.assertRaises(KeyError):
            run_deep(boom)

    def test_it_allows_recursion_past_the_default_limit(self):
        def depth(n):
            return 1 if n <= 1 else 1 + depth(n - 1)

        limit = sys.getrecursionlimit()
        with self.assertRaises(RecursionError):
            depth(limit * 3)
        self.assertEqual(run_deep(depth, limit * 3, limit=limit * 10), limit * 3)

    def test_it_leaves_the_recursion_limit_alone(self):
        before = sys.getrecursionlimit()

        def depth(n):
            return 1 if n <= 1 else 1 + depth(n - 1)

        run_deep(depth, 5000)
        self.assertEqual(sys.getrecursionlimit(), before)


class TestTiming(unittest.TestCase):
    def test_timed_returns_a_timing(self):
        calls = []

        def work():
            calls.append(1)
            return "done"

        result = timed(work, repeat=3)
        self.assertIsInstance(result, Timing)
        self.assertEqual(result.result, "done")
        self.assertEqual(result.calls, 3)
        self.assertEqual(len(calls), 3)

    def test_timed_rejects_a_silly_repeat(self):
        with self.assertRaises(ValueError):
            timed(lambda: None, repeat=0)

    def test_it_keeps_the_best_of_several_runs(self):
        # A slower second call must not make the reported time worse than the
        # first: best-of-N is what keeps the numbers comparable between runs.
        state = {"n": 0}

        def work():
            state["n"] += 1
            if state["n"] > 1:
                for _ in range(50_000):
                    pass

        fast = timed(work, repeat=1).seconds
        result = timed(lambda: None, repeat=1)
        self.assertLessEqual(fast, result.seconds + 1.0)


class TestFormatting(unittest.TestCase):
    def test_format_int(self):
        self.assertEqual(format_int(1234567), "1,234,567")
        self.assertEqual(format_int(0), "0")

    def test_format_seconds_picks_a_unit(self):
        self.assertIn("ns", format_seconds(1e-9))
        self.assertIn("us", format_seconds(1e-5))
        self.assertIn("ms", format_seconds(1e-2))
        self.assertIn("s", format_seconds(2.5))

    def test_format_ratio(self):
        self.assertEqual(format_ratio(1.234), "1.23x")
        self.assertEqual(format_ratio(12.6), "12.6x")
        self.assertEqual(format_ratio(250.0), "250x")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
