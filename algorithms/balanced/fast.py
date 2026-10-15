"""A better algorithm than "try every window": scan letter pairs instead.

The quadratic scans look at O(n^2) windows.  They get away with it because most
windows die immediately (a third letter appears), but they can still do O(n^2)
work on inputs like ``"abababab..."`` where nothing ever dies.

The key observation
-------------------
A balanced substring uses **exactly two distinct letters**.  With 26 letters
there are only ``26 * 25 / 2 = 325`` unordered pairs.  So:

1. Fix a pair ``{x, y}``.
2. Keep only the positions where ``x`` or ``y`` occurs.  Between gaps those
   positions form maximal **blocks**: any balanced substring made of ``x`` and
   ``y`` must live inside one block.
3. Inside a block, replace ``x`` by ``+1`` and ``y`` by ``-1``.  A substring has
   equal numbers of ``x`` and ``y`` exactly when the sum over it is ``0``,
   i.e. when two **prefix sums** are equal.  So the longest such substring ends
   where a prefix sum repeats, and starts at its *first* occurrence.

Step 3 is the classic "longest subarray with zero sum" trick; it turns "search
all windows" into "walk the block once and remember the first time you saw each
prefix value".

Two variants, and why both are here
-----------------------------------
``pair_scan``
    one pass: as it walks, every zero-sum interval that could still win is
    sliced, and the answer set is maintained live.  Simple, and the same walk
    produces a per-pair report for the trace files.

``pair_scan_two_pass``
    pass one computes the best length only -- no slicing at all; pass two walks
    the pairs again and slices *only* the substrings of exactly that length.
    Same answers, and the copying is proportional to the size of the answer
    rather than to how many candidates got considered along the way.

The difference is not small, and it is not the search: on ``"abababab..."`` at
n = 800, the single-pass version copies 320,000 characters' worth of improving
records while the two-pass version copies 800.  Both examine 1,600 positions.
This is the "O(n) search, O(n^2) copying bill" lesson from
``docs/05-complexity-lab.md``, made concrete.

Complexity
----------
Let ``k`` be how often the two letters of a pair occur.  One pair costs
``O(k log k)`` (the positions are sorted) and ``O(k)`` extra space.  Summed over
all 325 pairs, ``sum(k) = 25 * n``, so the search is ``O(26^2 * n log n)`` time
with a tiny constant.  ``pair_scan_two_pass`` adds ``O(answer size)`` copying.

Honesty note: this is *not* the asymptotically optimal solution.  There is a
family of genuinely linear-in-n algorithms for the "longest well-balanced
substring" problem (Huang, Liu & Wang, 2015) which handle the pairs *jointly*
with a clever encoding instead of one pair at a time.  What is here is the
version that fits on one page and can be checked against the oracle, which for a
teaching repository beats a linear algorithm nobody can read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from .core import BestTracker, normalize

__all__ = [
    "PairReport",
    "pair_scan",
    "pair_scan_normalized",
    "pair_scan_report",
    "pair_scan_two_pass",
    "pair_scan_two_pass_normalized",
]


@dataclass(frozen=True)
class PairReport:
    """One row of the pair-by-pair report (used by ``tools`` and the docs)."""

    pair: str
    blocks: int
    block_sizes: str
    best_length: int
    substrings: str


def pair_scan(s: Optional[str], *, casefold: bool = True) -> Tuple[int, List[str]]:
    """Longest balanced substring via the 325 letter pairs.

    >>> pair_scan("aabbb")
    (4, ['aabb'])
    >>> pair_scan("aabbc")
    (4, ['aabb'])
    >>> pair_scan("abcabc")
    (2, ['ab', 'bc', 'ca'])
    """
    return pair_scan_normalized(normalize(s, casefold=casefold))


def pair_scan_normalized(text: str) -> Tuple[int, List[str]]:
    """Same algorithm, assuming ``text`` is already normalised."""
    overall, _report = _pair_scan(text)
    return overall.result()


def pair_scan_two_pass(
    s: Optional[str], *, casefold: bool = True
) -> Tuple[int, List[str]]:
    """Same answers as :func:`pair_scan`, with the copying bill paid once.

    >>> pair_scan_two_pass("abcabc")
    (2, ['ab', 'bc', 'ca'])
    >>> pair_scan_two_pass("abab") == pair_scan("abab")
    True
    """
    return pair_scan_two_pass_normalized(normalize(s, casefold=casefold))


def pair_scan_two_pass_normalized(text: str) -> Tuple[int, List[str]]:
    """The core of :func:`pair_scan_two_pass`; ``text`` already validated."""
    positions = _positions(text)
    letters = sorted(positions)
    if len(letters) < 2:
        return 0, []

    best = 0
    for first, second in _pairs(letters):
        merged = _merged(positions, first, second)
        for start, end in _blocks(merged):
            best = max(best, _longest_in_block(text, merged, first, start, end, best))

    if best == 0:
        return 0, []

    found: Set[str] = set()
    for first, second in _pairs(letters):
        merged = _merged(positions, first, second)
        for start, end in _blocks(merged):
            _collect_in_block(text, merged, first, start, end, best, found)
    return best, sorted(found)


def pair_scan_report(text: str) -> List[PairReport]:
    """Per-pair diagnostics: how many blocks, and what each pair contributed."""
    _overall, report = _pair_scan(text)
    return report


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------


def _positions(text: str) -> Dict[str, List[int]]:
    positions: Dict[str, List[int]] = {}
    for index, ch in enumerate(text):
        positions.setdefault(ch, []).append(index)
    return positions


def _pairs(letters: Sequence[str]):
    for left in range(len(letters)):
        for right in range(left + 1, len(letters)):
            yield letters[left], letters[right]


def _merged(positions: Dict[str, List[int]], first: str, second: str) -> List[int]:
    """Positions of the two letters, sorted."""
    return sorted(positions[first] + positions[second])


def _blocks(merged: Sequence[int]):
    """Yield ``(start, end)`` index ranges: maximal runs of consecutive positions.

    Two entries belong to the same block when the second position is exactly one
    more than the first, i.e. when no other letter sits between them.  A balanced
    substring over ``{x, y}`` can only live inside one block.
    """
    start = 0
    for k in range(1, len(merged)):
        if merged[k] != merged[k - 1] + 1:
            yield start, k - 1
            start = k
    if merged:
        yield start, len(merged) - 1


def _walk_block(
    text: str,
    merged: Sequence[int],
    first_letter: str,
    lo: int,
    hi: int,
    on_match: Callable[[int, int], None],
) -> None:
    """Walk one block's prefix sums and report every repeated value.

    ``on_match(start_index, k)`` is called whenever ``merged[start_index..k]``
    contains as many copies of ``first_letter`` as of the other letter.  The map
    from prefix value to its *earliest* boundary index is what makes the longest
    match appear: a later boundary with a repeated value yields the substring
    ending there, and the earliest boundary yields the longest one.

    Passing a callback keeps the two variants (longest-only, and collect) on the
    same code path, so they cannot drift apart.
    """
    prefix = 0
    earliest: Dict[int, int] = {0: lo}  # boundary index -> prefix value at it
    for k in range(lo, hi + 1):
        prefix += 1 if text[merged[k]] == first_letter else -1
        start = earliest.get(prefix)
        if start is None:
            earliest[prefix] = k + 1
        else:
            on_match(start, k)


def _longest_in_block(
    text: str,
    merged: Sequence[int],
    first_letter: str,
    lo: int,
    hi: int,
    best_so_far: int,
) -> int:
    """Length of the longest zero-sum part of one block; no substrings are built."""
    best = [best_so_far]

    def on_match(start: int, k: int) -> None:
        length = merged[k] - merged[start] + 1
        if length > best[0]:
            best[0] = length

    _walk_block(text, merged, first_letter, lo, hi, on_match)
    return best[0]


def _collect_in_block(
    text: str,
    merged: Sequence[int],
    first_letter: str,
    lo: int,
    hi: int,
    target: int,
    found: Set[str],
) -> None:
    """Record every zero-sum part of this block whose length is ``target``."""

    def on_match(start: int, k: int) -> None:
        if merged[k] - merged[start] + 1 == target:
            found.add(text[merged[start] : merged[k] + 1])

    _walk_block(text, merged, first_letter, lo, hi, on_match)


# ---------------------------------------------------------------------------
# the single-pass variant (and its report)
# ---------------------------------------------------------------------------


def _pair_scan(text: str) -> Tuple[BestTracker, List[PairReport]]:
    overall = BestTracker()
    report: List[PairReport] = []
    positions = _positions(text)
    letters = sorted(positions)
    if len(letters) < 2:
        return overall, report

    for first_letter, second_letter in _pairs(letters):
        merged = _merged(positions, first_letter, second_letter)
        pair_tracker = BestTracker()
        block_sizes: List[int] = []

        for lo, hi in _blocks(merged):
            block_sizes.append(hi - lo + 1)

            def on_match(start: int, k: int, tracker=pair_tracker) -> None:
                # Build the substring only when it could still win: see
                # BestTracker.consider_span.  Without this guard the *scan*
                # stays O(n^2) but the program becomes O(n^3) on "ababab...".
                tracker.consider_span(text, merged[start], merged[k])

            _walk_block(text, merged, first_letter, lo, hi, on_match)

        # Only this pair's own longest matters globally: a shorter substring can
        # never be a global maximum.
        overall.merge(pair_tracker)
        report.append(
            PairReport(
                pair=first_letter + second_letter,
                blocks=len(block_sizes),
                block_sizes=" ".join(str(size) for size in block_sizes) or "-",
                best_length=pair_tracker.length,
                substrings=" ".join(pair_tracker.strings()) or "-",
            )
        )
    return overall, report
