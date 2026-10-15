"""Measure the algorithms: element reads and wall-clock time.

The two metrics answer different questions.

**Element reads** -- how many times the algorithm looked at a character or an
array slot -- is machine-independent and shows the *shape* of the cost
(doubling n quadruples the reads for an O(n^2) algorithm).  Reads are counted by
wrapping the input in :class:`algorithms.support.ReadCounter`.

**Wall-clock time** is what a user feels.  It is measured best-of-N to keep the
noise down, and it is only reported for inputs small enough to be interesting
rather than for inputs large enough to be slow.

    python -m tools.bench                 # both problems, default sizes
    python -m tools.bench --balanced      # just the balanced-string table
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import Callable, Dict, List, Sequence, Tuple

from algorithms import balanced, dominator
from algorithms.balanced.fast import pair_scan_normalized, pair_scan_two_pass_normalized
from algorithms.balanced.iterative import (
    brute_force_incremental_normalized,
    brute_force_normalized,
)
from algorithms.balanced.recursion import (
    recursive_normalized,
    recursive_shared_freq_normalized,
)
from algorithms.balanced.reference import reference_normalized
from algorithms.support import ReadCounter, format_int, format_seconds, timed
from algorithms.tracing import render_table

# ---------------------------------------------------------------------------
# input shapes
# ---------------------------------------------------------------------------


def shape_random(n: int, letters: int = 4, seed: int = 12345) -> str:
    """Random letters: most scans die early, so the quadratic scans look good."""
    rng = random.Random(seed)
    alphabet = "abcdefghijklmnopqrstuvwxyz"[:letters]
    return "".join(rng.choice(alphabet) for _ in range(n))


def shape_alternating(n: int, seed: int = 0) -> str:
    """``ababab...``: never a third letter, the worst case for the quadratic scans."""
    return ("ab" * ((n // 2) + 1))[:n]


def shape_single(n: int, seed: int = 0) -> str:
    """``aaaa...``: nothing ever dies, and nothing is ever balanced either."""
    return "a" * n


SHAPES: Dict[str, Callable[[int], str]] = {
    "random(4 letters)": shape_random,
    "abababab...": shape_alternating,
    "aaaa...": shape_single,
}

# ---------------------------------------------------------------------------
# balanced strings
# ---------------------------------------------------------------------------

BALANCED_CORES: Dict[str, Callable[[str], Tuple[int, List[str]]]] = {
    "reference (O(n^3))": reference_normalized,
    "brute_force": brute_force_normalized,
    "brute_force_incremental": brute_force_incremental_normalized,
    "recursive": recursive_normalized,
    "recursive_shared_freq": recursive_shared_freq_normalized,
    "pair_scan": pair_scan_normalized,
    "pair_scan_two_pass": pair_scan_two_pass_normalized,
}

#: Two hard limits, both worth stating out loud.
#:
#: * The oracle is here to be correct, not quick: n^3 is n^3.
#: * The recursive implementations use one stack frame per character of the
#:   window they scan, and CPython's default recursion limit is 1000, so 900
#:   characters is already close to the wall.  That wall is not a bug in this
#:   repository; it is the subject of docs/03-recursion-vs-iteration.md.
MAX_SIZE: Dict[str, int] = {
    "reference (O(n^3))": 400,
    "recursive": 900,
    "recursive_shared_freq": 900,
}


def balanced_table(
    sizes: Sequence[int] = (125, 250, 500, 1000, 2000),
    shape: str = "abababab...",
    repeat: int = 3,
) -> str:
    """Reads and time for every balanced implementation, on one input shape."""
    builder = SHAPES[shape]
    rows = []
    for name, core in BALANCED_CORES.items():
        for size in sizes:
            if size > MAX_SIZE.get(name, 10**9):
                rows.append((name, size, "-", "-", "-", "too slow to be useful here"))
                continue
            data = builder(size)
            counter = ReadCounter(data)
            try:
                core(counter)  # the measuring run: counts every element read
                timing = timed(core, data, repeat=repeat)  # the timing runs
            except RecursionError:
                rows.append((name, size, "-", "-", "-", "RecursionError: depth ~ n"))
                continue
            length, answers = timing.result  # type: ignore[misc]
            rows.append(
                (
                    name,
                    size,
                    format_int(counter.point_reads),
                    format_int(counter.slice_reads),
                    format_seconds(timing.seconds),
                    f"length {length}, {len(answers)} answer(s)",
                )
            )
        rows.append(("", "", "", "", "", ""))
    return render_table(
        ["implementation", "n", "positions", "slices", "best of %d" % repeat, "result"],
        rows,
        align=["<", ">", ">", ">", ">", "<"],
    )


# ---------------------------------------------------------------------------
# dominators
# ---------------------------------------------------------------------------

DOMINATOR_CORES: Dict[str, Callable[[Sequence], object]] = {
    "boyer_moore": dominator.boyer_moore,
    "divide_and_conquer": dominator.divide_and_conquer,
    "index_cache": dominator.index_cache,
    "sort_and_pick_middle": dominator.sort_and_pick_middle,
}


def dominator_input(n: int, *, has_dominator: bool, seed: int = 7) -> List[int]:
    rng = random.Random(seed)
    if not has_dominator:
        return [rng.randint(0, 9) for _ in range(n)]
    # Two thirds of the array is one value: a dominator exists and the
    # verification pass finds it.
    count = 2 * (n // 3) + 1
    values = [1] * count + [rng.randint(2, 9) for _ in range(n - count)]
    rng.shuffle(values)
    return values


def dominator_table(
    sizes: Sequence[int] = (1000, 10000, 100000),
    *,
    has_dominator: bool = True,
    repeat: int = 3,
) -> str:
    rows = []
    for name, core in DOMINATOR_CORES.items():
        for size in sizes:
            data = dominator_input(size, has_dominator=has_dominator)
            counter = ReadCounter(data)
            core(counter)  # measuring run
            timing = timed(core, data, repeat=repeat)  # timing runs
            answer = timing.result  # type: ignore[assignment]
            rows.append(
                (
                    name,
                    size,
                    format_int(counter.point_reads),
                    format_int(counter.slice_reads),
                    format_seconds(timing.seconds),
                    "-" if answer is None else str(answer.count),
                )
            )
        rows.append(("", "", "", "", "", ""))
    return render_table(
        ["implementation", "n", "positions", "slices", "best of %d" % repeat, "dominator count"],
        rows,
        align=["<", ">", ">", ">", ">", ">"],
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balanced", action="store_true", help="only the balanced-string tables")
    parser.add_argument("--dominator", action="store_true", help="only the dominator tables")
    parser.add_argument("--repeat", type=int, default=3, help="best-of-N timing runs")
    parser.add_argument(
        "--sizes",
        default="125,250,500,1000,2000",
        help="comma-separated sizes for the balanced tables",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    sizes = [int(part) for part in args.sizes.split(",") if part.strip()]

    do_balanced = args.balanced or not args.dominator
    do_dominator = args.dominator or not args.balanced

    if do_balanced:
        for shape in SHAPES:
            print()
            print(f"Balanced substrings -- input shape: {shape}")
            print(balanced_table(sizes, shape=shape, repeat=args.repeat))
        print()
        print("Note how 'random(4 letters)' flatters the quadratic scans: with four")
        print("letters, almost every scan dies at the third character.  The 'abab'")
        print("and 'aaaa' shapes are the honest worst cases.")

    if do_dominator:
        for has_dominator in (True, False):
            print()
            print(f"Dominators -- {'a dominator exists' if has_dominator else 'no dominator'}")
            print(dominator_table(has_dominator=has_dominator, repeat=args.repeat))

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
