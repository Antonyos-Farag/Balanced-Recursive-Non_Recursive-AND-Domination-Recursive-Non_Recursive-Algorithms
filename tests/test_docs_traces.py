"""The traces quoted in ``docs/`` must match the code that produced them.

Documentation rots quietly: a function is renamed, an output changes, and the
printout in chapter three stays exactly as it was, looking authoritative.  This
test compares every file in ``docs/traces/`` against a fresh run.

    python -m tools.make_traces          # fix a stale file

The benchmark file is exempt: timings change from machine to machine, so it is
checked for existence and shape only.
"""

from __future__ import annotations

import unittest

from tools import make_traces


class TestDocTraces(unittest.TestCase):
    def test_every_deterministic_trace_is_current(self):
        for name, builder in make_traces.DETERMINISTIC.items():
            path = make_traces.TRACE_DIR / name
            with self.subTest(trace=name):
                self.assertTrue(path.exists(), f"{name} is missing: run python -m tools.make_traces")
                self.assertEqual(
                    path.read_text(encoding="utf-8"),
                    builder(),
                    f"{name} is stale: run python -m tools.make_traces",
                )

    def test_the_benchmark_trace_exists_and_is_labelled(self):
        path = make_traces.TRACE_DIR / "bench.txt"
        self.assertTrue(path.exists(), "run python -m tools.make_traces")
        text = path.read_text(encoding="utf-8")
        self.assertIn("timings depend on the machine", text.lower())
        self.assertIn("implementation", text)

    def test_no_orphan_files_in_the_trace_directory(self):
        known = set(make_traces.DETERMINISTIC) | set(make_traces.NON_DETERMINISTIC)
        for path in make_traces.TRACE_DIR.glob("*.txt"):
            with self.subTest(trace=path.name):
                self.assertIn(path.name, known, "add the file to tools/make_traces.py")

    def test_every_trace_file_has_the_warning_header(self):
        for path in make_traces.TRACE_DIR.glob("*.txt"):
            with self.subTest(trace=path.name):
                head = path.read_text(encoding="utf-8")[:200]
                self.assertIn("Regenerate with", head)

    def test_the_check_command_agrees_with_the_tests(self):
        self.assertEqual(make_traces.check(), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
