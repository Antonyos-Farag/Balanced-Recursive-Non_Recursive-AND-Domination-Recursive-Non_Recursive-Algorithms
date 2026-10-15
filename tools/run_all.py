"""Run the whole repository: tests, trace check, archive check, then the tour.

    python -m tools.run_all [--no-demo]

This is the command to run before committing, and the command a reader can run
to reproduce every number in ``docs/``.  It exits non-zero on the first failure.

If ``node`` is installed the playground's JavaScript is cross-checked against
the Python implementations as well (``tools/check_playground.py``); without node
that step says so and is skipped, because nothing in the Python repository
depends on a JavaScript runtime.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import List, Sequence

from tools import check_playground, freeze_archive, make_traces


def run(command: List[str]) -> bool:
    print("$ " + " ".join(command))
    started = time.perf_counter()
    completed = subprocess.run(command)
    elapsed = time.perf_counter() - started
    status = "ok" if completed.returncode == 0 else f"FAILED ({completed.returncode})"
    print(f"  -> {status} in {elapsed:.2f}s\n")
    return completed.returncode == 0


def main(argv: Sequence[str] | None = None) -> int:
    show_demo = "--no-demo" not in (argv or sys.argv[1:])

    steps = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
        [sys.executable, "-m", "tools.make_traces", "--check"],
    ]
    for step in steps:
        if not run(step):
            return 1

    if freeze_archive.main(["--check"]) != 0:
        return 1
    if check_playground.main([]) != 0:
        return 1
    print()

    if show_demo:
        if not run([sys.executable, "-m", "tools.demo"]):
            return 1

    print("everything passed.  docs/traces/*.txt is up to date with the code.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
