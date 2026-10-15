"""Non-recursive balanced strings: the loop version and its round trip.

Two functions live here and they exist to be compared.

``brute_force``
    The repaired version of the submitted non-recursive program.  One fix, and
    it is a *one-line* fix: the "is this window balanced?" test has to happen
    **inside** the ``end`` loop, once per window, not after the ``end`` loop has
    already finished.  ``docs/04-bug-hunt.md`` bug B1 is exactly that indentation.

``round_trip``
    The same algorithm written by mechanically unrolling the *recursive*
    program: ``TryStart`` becomes the outer ``for``, ``TryEnd`` becomes the
    inner ``for``, and the arguments that used to travel down the call chain
    become ordinary local variables.  Two programs that look nothing alike end
    up as the same loop, which is the whole lesson of
    ``docs/03-recursion-vs-iteration.md``.

``brute_force_incremental``
    The same O(n^2) scan with an **O(1)** balance test.  Instead of walking the
    26-slot table, it tracks the largest count in the window; with exactly two
    distinct letters, the counts are equal exactly when the largest one is half
    the window.  Same answers, same reads, and 2x faster on random text -- the
    26-slot scan *is* the constant factor of the "quadratic" algorithm.

All three are O(n^2) time and O(1) extra space beyond the answers: the frequency
table is reset once per start and mutated in place as ``end`` advances.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..tracing import TraceLog
from .core import _A, BestTracker, equal_pair, freq_summary, normalize

__all__ = [
    "brute_force",
    "brute_force_incremental",
    "brute_force_incremental_normalized",
    "brute_force_normalized",
    "round_trip",
    "round_trip_normalized",
]


def brute_force(
    s: Optional[str],
    *,
    casefold: bool = True,
    trace: Optional[TraceLog] = None,
) -> Tuple[int, List[str]]:
    """Repaired O(n^2) scan.

    >>> brute_force("aabbb")
    (4, ['aabb'])
    >>> brute_force("aabbc")
    (4, ['aabb'])
    >>> brute_force("abcabc")
    (2, ['ab', 'bc', 'ca'])
    """
    text = normalize(s, casefold=casefold)
    return brute_force_normalized(text, trace=trace)


def brute_force_normalized(
    text: str, *, trace: Optional[TraceLog] = None
) -> Tuple[int, List[str]]:
    """The core of :func:`brute_force`, with ``text`` already validated."""
    tracker = BestTracker()
    n = len(text)

    for start in range(n):
        freq = [0] * 26  # fresh table per start: every window begins here
        distinct = 0  # how many different letters the window [start, end] uses
        for end in range(start, n):
            index = ord(text[end]) - _A
            if freq[index] == 0:
                distinct += 1
            freq[index] += 1

            if distinct > 2:
                # `distinct` only ever grows as `end` grows, so once a third
                # letter appears no longer window can ever be balanced: stop.
                if trace is not None:
                    trace.event(
                        "window",
                        start=start,
                        end=end,
                        window=text[start : end + 1],
                        counts=freq_summary(freq),
                        distinct=distinct,
                        verdict="3rd letter -> stop",
                        best=tracker.length,
                    )
                break

            if distinct < 2:
                verdict = "needs two letters"
            elif equal_pair(freq):
                verdict = "balanced <--"
                tracker.consider_span(text, start, end)
            else:
                verdict = "counts differ"

            if trace is not None:
                trace.event(
                    "window",
                    start=start,
                    end=end,
                    window=text[start : end + 1],
                    counts=freq_summary(freq),
                    distinct=distinct,
                    verdict=verdict,
                    best=tracker.length,
                )

    return tracker.result()


def brute_force_incremental(
    s: Optional[str], *, casefold: bool = True
) -> Tuple[int, List[str]]:
    r"""The same scan with an O(1) balance test instead of a 26-slot one.

    The test in :func:`brute_force` walks all 26 slots of the frequency table for
    every window.  That is the algorithm's dominant cost, and it can be replaced
    by two integers:

    * ``distinct`` -- how many different letters the window uses (already
      maintained);
    * ``max_count`` -- the largest count in the table, updated in O(1) when the
      incoming letter is counted.

    **Claim:** when ``distinct == 2``, the two counts are equal if and only if
    ``2 * max_count == window length``.  If the counts are equal, each is half
    the length and so is the larger one.  If the larger one is half the length,
    the other one must be as well, because together they are the whole window.

    Measured (n = 1,000, best of five, same machine as ``docs/traces/bench.txt``):

    ===================  ============  ===============  ==========
    shape                brute_force   incremental      ratio
    ===================  ============  ===============  ==========
    random over abcd     1.77 ms       0.83 ms          **2.1x faster**
    ``"ababab..."``      303 ms        80.4 ms          **3.8x faster**
    ``"aaaa..."``        46.5 ms       51.3 ms          10% slower
    ===================  ============  ===============  ==========

    The read counts are *identical* to :func:`brute_force` on all three shapes
    -- the improvement is purely the constant factor, which is exactly what an
    element-read counter cannot see and a stopwatch can.

    >>> brute_force_incremental("aabbc")
    (4, ['aabb'])
    >>> brute_force_incremental("abcabc") == brute_force("abcabc")
    True
    """
    text = normalize(s, casefold=casefold)
    return brute_force_incremental_normalized(text)


def brute_force_incremental_normalized(text: str) -> Tuple[int, List[str]]:
    """The core of :func:`brute_force_incremental`; ``text`` already validated."""
    tracker = BestTracker()
    n = len(text)

    for start in range(n):
        freq = [0] * 26
        distinct = 0
        max_count = 0
        for end in range(start, n):
            index = ord(text[end]) - _A
            if freq[index] == 0:
                distinct += 1
            freq[index] += 1
            if freq[index] > max_count:
                max_count = freq[index]

            if distinct > 2:
                break

            if distinct == 2 and 2 * max_count == end - start + 1:
                tracker.consider_span(text, start, end)

    return tracker.result()


def round_trip(s: Optional[str], *, casefold: bool = True) -> Tuple[int, List[str]]:
    """The recursive program with both recursions turned into loops.

    The comments map every line back to ``TryStart`` / ``TryEnd`` in
    ``algorithms/original/balanced_recursive.py``.

    >>> round_trip("aabbb") == brute_force("aabbb")
    True
    """
    text = normalize(s, casefold=casefold)
    return round_trip_normalized(text)


def round_trip_normalized(text: str) -> Tuple[int, List[str]]:
    """The core of :func:`round_trip`, with ``text`` already validated."""
    n = len(text)
    tracker = BestTracker()

    # TryStart(S, n, start, longest, best_list) -- one call per start, and the
    # only thing that ever changes between those calls is `start`, so the tail
    # recursion becomes this loop.
    for start in range(n):
        freq = [0] * 26  # TryStart builds a fresh table for each start
        distinct = 0
        for end in range(start, n):  # TryEnd(S, n, start, end, freq, ...)
            if text[end].isalpha():
                index = ord(text[end]) - _A
                if freq[index] == 0:
                    distinct += 1
                freq[index] += 1

                if distinct > 2:
                    break  # TryEnd's "if distinct > 2: return"

                if distinct == 2 and equal_pair(freq):
                    tracker.consider_span(text, start, end)

            # TryEnd recursed with `end + 1`; the loop does it for us.
    return tracker.result()
