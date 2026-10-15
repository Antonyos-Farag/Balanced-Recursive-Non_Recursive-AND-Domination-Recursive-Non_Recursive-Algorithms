"""Regenerate ``docs/traces/*.txt`` -- the program output quoted in the docs.

Every block of program output in ``docs/`` is written to a file here, so it can
be regenerated instead of trusted:

    python -m tools.make_traces          # rewrite the files
    python -m tools.make_traces --check  # fail if anything is out of date

``tests/test_docs_traces.py`` imports :data:`DETERMINISTIC` and does the same
check from inside the test suite.  The benchmark file is deliberately *not* in
that set: timings differ from machine to machine, so it is regenerated but not
compared.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Callable, Dict, Sequence

from algorithms import tracing
from algorithms.support import format_int
from algorithms.tracing import render_table
from tools.demo import bug_table, dominator_table

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRACE_DIR = ROOT / "docs" / "traces"

HEADER = (
    "# {title}\n"
    "#\n"
    "# Regenerate with:  python -m tools.make_traces\n"
    "# Do not edit by hand: tests/test_docs_traces.py compares this file with a\n"
    "# fresh run of the code it shows.\n"
)


def _wrap(title: str, body: str) -> str:
    return HEADER.format(title=title) + "\n" + body.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# the deterministic traces
# ---------------------------------------------------------------------------


def balanced_scan_trace() -> str:
    """The fixed O(n^2) scan, window by window."""
    parts = [
        "## brute_force('aabbb') -- the fixed scan",
        "",
        "Every window the scan looks at, with the frequency table at that moment.",
        "The 'balanced <--' rows are the windows that count.",
        "",
        tracing.scan_table("aabbb"),
        "",
        "## brute_force('aabbc')",
        "",
        "Same scan, with a third letter appearing at the end of the first start.",
        "",
        tracing.scan_table("aabbc"),
    ]
    return _wrap("element-by-element trace of the repaired quadratic scan", "\n".join(parts))


def balanced_bug_table() -> str:
    """Every program, every example input, and the verdict."""
    parts = [
        "## the same inputs through every program",
        "",
        "'correct answer' is algorithms.balanced.reference, the O(n^3) oracle.",
        "",
        bug_table(),
        "",
        "## the dominators, the same way",
        "",
        dominator_table(),
    ]
    return _wrap("four programs, one problem, three answers", "\n".join(parts))


def balanced_recursive_tree() -> str:
    parts = [
        "## recursive_call_tree('aabbb') -- the repaired recursion",
        "",
        "One node per TryEnd call.  The value after '->' is what the original",
        "returned up the call chain: (longest so far, answers so far).  Because the",
        "accumulator is shared, the same values come back out of every node.",
        "",
        tracing.recursive_call_tree("aabbb"),
        "",
        "## recursive_call_tree('aabbc') -- note where the scans stop",
        "",
        tracing.recursive_call_tree("aabbc"),
    ]
    return _wrap("the repaired recursive scan as a call tree", "\n".join(parts))


def balanced_original_tree() -> str:
    parts = [
        "## the *archived* recursion, traced by patching the module at run time",
        "",
        "TryStart and TryEnd are looked up in the module's globals on every call, so",
        "replacing those two names with wrappers intercepts the recursion without",
        "editing a line of the submission.  Note the empty TryEnd frames at",
        "end == n: the scan always takes one step past the last character.",
        "",
        tracing.original_call_tree("aabb"),
        "",
        "## the same tree for 'aabbb'",
        "",
        "The freq column lists the non-zero counts in alphabet order as they stand",
        "*on entry* to the call -- the call then folds S[end] into them.  So the",
        "frame at end=3 (freq [2, 1], the window 'aab') is the one that adds the",
        "second 'b' and records 'aabb'; the frame below it already holds [2, 2].",
        "",
        "The scan carries on to end=5, where the whole string 'aabbb' has counts 2",
        "and 3 and is not balanced -- but the answer (4, ['aabb']) stays on the",
        "books.  The recursive submission is *right* here.  The loop submission,",
        "given exactly the same string, answers (0, []): see balanced-bug-table.txt.",
        "",
        tracing.original_call_tree("aabbb"),
    ]
    return _wrap("the submitted recursion (also known as `TryStart` / `TryEnd`)", "\n".join(parts))


def balanced_pairs_trace() -> str:
    parts = [
        "## pair_scan('aabbc') -- one row per letter pair",
        "",
        "'blocks' counts the maximal runs of consecutive positions occupied by the",
        "two letters; 'block sizes' shows how long those runs are.  A balanced",
        "substring can only live inside a block, which is why the pair (a, c) -- with",
        "blocks 'aa' and 'c' -- contributes nothing.",
        "",
        tracing.pair_scan_table("aabbc"),
        "",
        "## pair_scan('abcabc')",
        "",
        tracing.pair_scan_table("abcabc"),
    ]
    return _wrap("the pair scan: 325 letter pairs, blocks, prefix sums", "\n".join(parts))


def dominator_vote_trace() -> str:
    parts = [
        "## Boyer-Moore on [3, 1, 3, 2, 3, 4, 3, 3]",
        "",
        "The vote leaves candidate 3 with count 2; the verification pass counts 5",
        "real occurrences, which is more than 8 // 2 = 4, so 3 is a dominator.",
        "The count column is the vote's bookkeeping, *not* a count of occurrences.",
        "",
        tracing.vote_table([3, 1, 3, 2, 3, 4, 3, 3]),
        "",
        "## ... and on [1, 2, 3], where the vote is wrong",
        "",
        "Candidate 3 survives the vote, but it occurs once in three elements, so the",
        "verification pass throws it away.  Removing that second pass is the classic",
        "way to get this exercise wrong.",
        "",
        tracing.vote_table([1, 2, 3]),
    ]
    return _wrap("Boyer-Moore: cancel, elect, and verify", "\n".join(parts))


def dominator_divide_trace() -> str:
    parts = [
        "## divide_and_conquer([3, 1, 3, 2, 3, 4, 3, 3])",
        "",
        "Each node shows its range and the answer it returned; '-' means 'this range",
        "has no dominator'.  Follow the right half: 3 dominates [4..7] because it is",
        "the candidate of both its halves.",
        "",
        tracing.divide_conquer_tree([3, 1, 3, 2, 3, 4, 3, 3]),
        "",
        "## the same recursion on [3, 1, 3, 2] -- where it returns nothing",
        "",
        "No half has a dominator, so no range above them can have one either.  That",
        "is the halving lemma doing the work: it is what makes 'nothing' a safe",
        "answer to propagate upwards.",
        "",
        tracing.divide_conquer_tree([3, 1, 3, 2]),
    ]
    return _wrap("the divide & conquer dominator as a call tree", "\n".join(parts))


def balanced_scaling_trace() -> str:
    """Reads, not time: machine-independent evidence of the complexity classes."""
    from algorithms.balanced.fast import (
        pair_scan_normalized,
        pair_scan_two_pass_normalized,
    )
    from algorithms.balanced.iterative import brute_force_normalized
    from algorithms.balanced.recursion import recursive_shared_freq_normalized
    from algorithms.balanced.reference import reference_normalized
    from algorithms.support import ReadCounter

    # name -> (core, sizes that finish quickly enough to be worth printing)
    cores = [
        ("reference (n^3)", reference_normalized, (25, 50, 100)),
        ("brute_force (n^2)", brute_force_normalized, (100, 200, 400, 800)),
        ("recursive_shared_freq (n^2)", recursive_shared_freq_normalized, (100, 200, 400)),
        ("pair_scan", pair_scan_normalized, (100, 200, 400, 800)),
        ("pair_scan_two_pass", pair_scan_two_pass_normalized, (100, 200, 400, 800)),
    ]

    rows = []
    for name, core, sizes in cores:
        previous_points = None
        previous_slices = None
        for size in sizes:
            text = ("ab" * (size // 2 + 1))[:size]
            counter = ReadCounter(text)
            core(counter)
            points, slices = counter.point_reads, counter.slice_reads

            def growth(now, before):
                # 0 reads of a kind means "-": the reference, for instance, never
                # touches an element directly, it only ever copies slices.
                if before is None or before == 0:
                    return "-"
                return f"x{now / before:.1f}"

            rows.append(
                (
                    name,
                    size,
                    format_int(points),
                    growth(points, previous_points),
                    format_int(slices),
                    growth(slices, previous_slices),
                )
            )
            previous_points, previous_slices = points, slices
        rows.append(("", "", "", "", "", ""))

    return _wrap(
        "element reads on 'ababab...' (the quadratic scans' worst case)",
        "positions = single-element reads: the search itself.\n"
        "slices    = characters copied while materialising answers.\n"
        "Each growth column compares with the previous doubling of n.\n"
        "\n"
        "Doubling n multiplies *positions* by about 4 for the quadratic scans and by\n"
        "about 2 for the pair scan -- the complexity classes, measured rather than\n"
        "asserted.  The reference shows 0 positions because it works by slicing: it\n"
        "copies every window it looks at, so all of its work lands in the slices\n"
        "column, where the growth is about 8 (its cost is n^3).\n"
        "\n"
        "The pair scan is the interesting row: its search is linear, yet its slices\n"
        "grow fourfold, because every candidate that improves the record is copied,\n"
        "and the records get longer as it goes.  pair_scan_two_pass walks the pairs\n"
        "twice -- once to learn the best length, once to collect the answers of that\n"
        "length -- and pays 1.5x the positions to cut the slices from n^2/2 to n.\n"
        "\n"
        "Wall-clock time (bench.txt) shows which bill actually hurts: copying\n"
        "characters is a memcpy in C, while the quadratic scans spend their time in\n"
        "the Python interpreter.  Quadratic search work is not the same problem as\n"
        "quadratic copying work, and a good measurement keeps them apart.\n\n"
        + render_table(
            ["implementation", "n", "positions", "pos growth", "slices", "slice growth"],
            rows,
            align=["<", ">", ">", ">", ">", ">"],
        ),
    )


DETERMINISTIC: Dict[str, Callable[[], str]] = {
    "balanced-scan.txt": balanced_scan_trace,
    "balanced-bug-table.txt": balanced_bug_table,
    "balanced-recursive-tree.txt": balanced_recursive_tree,
    "balanced-original-tree.txt": balanced_original_tree,
    "balanced-pairs.txt": balanced_pairs_trace,
    "balanced-scaling.txt": balanced_scaling_trace,
    "dominator-vote.txt": dominator_vote_trace,
    "dominator-divide-tree.txt": dominator_divide_trace,
}


# ---------------------------------------------------------------------------
# the one file that is allowed to change between runs
# ---------------------------------------------------------------------------


def bench_trace() -> str:
    from tools import bench

    parts = [
        "## timings and element reads",
        "",
        "Timings depend on the machine; the *shape* of the tables does not.  These",
        "numbers were produced by `python -m tools.bench --sizes 125,250,500,1000`.",
        "Reads are counted in a separate single run, so `repeat` does not inflate them.",
        "",
    ]
    for shape in bench.SHAPES:
        parts.append(f"### input shape: {shape}")
        parts.append("")
        parts.append("```")
        parts.append(bench.balanced_table((125, 250, 500, 1000), shape=shape, repeat=3))
        parts.append("```")
        parts.append("")
    for has_dominator in (True, False):
        label = "a dominator is present" if has_dominator else "no dominator at all"
        parts.append(f"### dominators, {label}")
        parts.append("")
        parts.append("```")
        parts.append(bench.dominator_table((10_000, 100_000), has_dominator=has_dominator, repeat=3))
        parts.append("```")
        parts.append("")
    return _wrap("the benchmark run behind docs/05-complexity-lab.md", "\n".join(parts))


NON_DETERMINISTIC = {"bench.txt": bench_trace}


def write_all(write_bench: bool = True) -> None:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in DETERMINISTIC.items():
        (TRACE_DIR / name).write_text(builder(), encoding="utf-8")
        print(f"wrote docs/traces/{name}")
    if write_bench:
        (TRACE_DIR / "bench.txt").write_text(bench_trace(), encoding="utf-8")
        print("wrote docs/traces/bench.txt (timings: not drift-checked)")


def check() -> int:
    stale = []
    for name, builder in DETERMINISTIC.items():
        path = TRACE_DIR / name
        expected = builder()
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            stale.append(name)
    if stale:
        print("stale traces: " + ", ".join(stale), file=sys.stderr)
        print("run: python -m tools.make_traces", file=sys.stderr)
        return 1
    print(f"{len(DETERMINISTIC)} trace files are up to date")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write; fail if stale")
    parser.add_argument("--no-bench", action="store_true", help="skip the slow benchmark file")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.check:
        return check()
    write_all(write_bench=not args.no_bench)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
