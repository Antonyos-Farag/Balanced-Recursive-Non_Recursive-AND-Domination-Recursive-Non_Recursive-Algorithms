"""Tests for the instrumentation the documentation leans on.

Every trace in ``docs/traces/`` is produced by these functions, so if a renderer
silently changes shape (or stops truncating, and generates a 40 MB file), the
docs go wrong quietly.  These tests are the alarm.
"""

from __future__ import annotations

import unittest

from algorithms import tracing
from algorithms.original import balanced_recursive as legacy


class TestRenderTable(unittest.TestCase):
    def test_basic_shape(self):
        table = tracing.render_table(["a", "b"], [[1, 2], [300, 4]])
        lines = table.splitlines()
        self.assertEqual(len(lines), 6)  # top, header, rule, 2 rows, bottom
        self.assertTrue(lines[0].startswith("+"))
        self.assertIn("| a   |", lines[1] + " ")
        self.assertIn("300", lines[4])

    def test_alignment_is_per_column(self):
        table = tracing.render_table(["left", "right"], [["x", "y"]], align=["<", ">"])
        row = table.splitlines()[3]
        self.assertTrue(row.startswith("| x "))
        self.assertTrue(row.rstrip().endswith("|     y |"))

    def test_width_mismatch_is_an_error(self):
        with self.assertRaises(ValueError):
            tracing.render_table(["a", "b"], [[1]])
        with self.assertRaises(ValueError):
            tracing.render_table(["a", "b"], [[1, 2]], align=["<"])

    def test_empty_table_still_renders_headers(self):
        table = tracing.render_table(["only"], [])
        self.assertIn("only", table)


class TestRenderBar(unittest.TestCase):
    def test_full_and_empty(self):
        self.assertEqual(tracing.render_bar(10, 10, width=5), "#####")
        self.assertEqual(tracing.render_bar(0, 10, width=5), ".....")

    def test_zero_maximum_is_blank(self):
        self.assertEqual(tracing.render_bar(1, 0, width=4), "    ")

    def test_it_never_overflows(self):
        self.assertEqual(len(tracing.render_bar(100, 10, width=7)), 7)
        self.assertEqual(len(tracing.render_bar(-5, 10, width=7)), 7)


class TestTraceLog(unittest.TestCase):
    def test_tree_nesting(self):
        log = tracing.TraceLog()
        log.enter("outer", x=1)
        log.enter("inner", y=2)
        log.exit("inner", result=99)
        log.exit("outer")
        text = log.tree()
        self.assertIn("outer(x=1)", text)
        self.assertIn("inner(y=2)  -> 99", text)
        self.assertLess(text.index("outer"), text.index("inner"))

    def test_events_are_filterable(self):
        log = tracing.TraceLog()
        log.event("window", start=0)
        log.event("count", value=3)
        log.event("window", start=1)
        self.assertEqual([e["start"] for e in log.events("window")], [0, 1])
        self.assertEqual(len(log.events()), 3)

    def test_unbalanced_exit_is_an_error(self):
        log = tracing.TraceLog()
        with self.assertRaises(RuntimeError):
            log.exit("nobody")

    def test_truncation_is_reported_not_hidden(self):
        log = tracing.TraceLog(max_entries=3)
        for _ in range(10):
            log.enter("call")
        self.assertTrue(log.truncated)
        self.assertEqual(len(log), 3)
        self.assertIn("truncated", log.tree())
        # ...and the log stays balanced even though nodes were dropped.
        for _ in range(10):
            log.exit("call")
        self.assertEqual(log.depth, 1)

    def test_max_entries_must_be_sane(self):
        with self.assertRaises(ValueError):
            tracing.TraceLog(max_entries=0)

    def test_bool_reflects_whether_anything_happened(self):
        log = tracing.TraceLog()
        self.assertFalse(log)
        log.enter("x")
        self.assertTrue(log)


class TestTheSpecificTraces(unittest.TestCase):
    def test_scan_table_shows_every_window(self):
        table = tracing.scan_table("aab")
        self.assertIn("window seen", table)
        self.assertIn("balanced <--", table)  # the window "ab"
        self.assertIn("3rd letter", tracing.scan_table("aabbc"))

    def test_scan_table_can_limit_its_rows(self):
        table = tracing.scan_table("aabbccddee", max_rows=3)
        self.assertIn("more rows not shown", table)

    def test_recursive_call_tree(self):
        text = tracing.recursive_call_tree("aab")
        self.assertIn("TryEnd(start=0, end=0)", text)
        self.assertIn("TryEnd(start=1, end=2)", text)

    def test_original_call_tree_shows_both_functions(self):
        text = tracing.original_call_tree("aabb")
        self.assertIn("TryStart(", text)
        self.assertIn("TryEnd(", text)

    def test_original_call_tree_puts_the_module_back(self):
        before = (legacy.TryStart, legacy.TryEnd)
        tracing.original_call_tree("aabb")
        self.assertIs(legacy.TryStart, before[0])
        self.assertIs(legacy.TryEnd, before[1])
        self.assertEqual(legacy.LBS("aabb"), (4, ["aabb"]))  # still works

    def test_vote_table(self):
        table = tracing.vote_table([3, 1, 3, 2, 3, 4, 3, 3])
        self.assertIn("verify", table)
        self.assertIn("majority needs > 4", table)

    def test_vote_table_on_an_empty_array(self):
        self.assertIn("nothing to vote", tracing.vote_table([]))

    def test_divide_conquer_tree(self):
        text = tracing.divide_conquer_tree([3, 1, 3, 2, 3, 4, 3, 3])
        self.assertIn("majority(lo=0, hi=7)", text)
        self.assertIn("majority(lo=0, hi=0)", text)

    def test_pair_scan_table(self):
        table = tracing.pair_scan_table("aabbc")
        self.assertIn("block sizes", table)
        self.assertIn("aabb", table)
        self.assertIn("best over all pairs: 4", table)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
