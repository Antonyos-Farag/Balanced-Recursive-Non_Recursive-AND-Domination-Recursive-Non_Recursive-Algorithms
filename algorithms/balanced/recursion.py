"""Recursive balanced strings: the repaired ``TryStart`` / ``TryEnd`` scan.

The submitted recursion has the same bug as the submitted loop (the balance test
ran after the scan instead of during it), and it has two shapes worth studying:

* ``TryStart`` is **tail recursion** -- its last act is ``return TryStart(...)``
  with nothing done afterwards.  Tail recursion is a loop wearing a costume;
  here it is written as a loop, and ``algorithms/balanced/iterative.round_trip``
  finishes the job by unrolling ``TryEnd`` too.
* ``TryEnd`` is **structural recursion** -- each call walks one character
  further and the intermediate states are what the answer depends on.  It stays
  recursive, because that is where the call tree is interesting.

Two flavours of the inner scan are provided, because the difference between them
is one of the most useful ideas in recursive programming:

``recursive``
    Copy the frequency table before going deeper (``freq[:]``).  Each call owns
    its private copy, so nothing has to be undone.  Cost: 26 integers copied per
    level, per start.

``recursive_shared_freq``
    Mutate **one** table going down and undo the mutation coming back up -- the
    classic backtracking pattern.  Same answers, no copying.  It is measurably
    faster; see ``docs/03-recursion-vs-iteration.md``.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..support import run_deep
from ..tracing import TraceLog
from .core import _A, BestTracker, equal_pair, normalize

__all__ = [
    "recursive",
    "recursive_normalized",
    "recursive_shared_freq",
    "recursive_shared_freq_normalized",
    "recursive_deep",
    "recursive_depth",
]


def recursive(
    s: Optional[str],
    *,
    casefold: bool = True,
    trace: Optional[TraceLog] = None,
) -> Tuple[int, List[str]]:
    """Repaired recursive scan; returns ``(length, sorted substrings)``.

    >>> recursive("aabbb")
    (4, ['aabb'])
    >>> recursive("abcabc")
    (2, ['ab', 'bc', 'ca'])

    Depth is one stack frame per character of the window being scanned plus one,
    so a window longer than ~990 characters hits CPython's default recursion
    limit -- see :func:`recursive_deep` for the way out.
    """
    text = normalize(s, casefold=casefold)
    return recursive_normalized(text, trace=trace)


def recursive_normalized(
    text: str, *, trace: Optional[TraceLog] = None
) -> Tuple[int, List[str]]:
    """The core of :func:`recursive`, with ``text`` already validated.

    Exposed because ``docs/05-complexity-lab.md`` measures how many characters
    the algorithm reads, and for that the input has to be wrapped in a counting
    proxy instead of being rebuilt by :func:`~algorithms.balanced.core.normalize`.
    """
    tracker = BestTracker()
    for start in range(len(text)):
        # `freq`/`distinct` are created here and handed down, exactly like the
        # original's TryStart does before its first TryEnd call.
        _try_end(text, start, start, [0] * 26, 0, tracker, trace)
    return tracker.result()


def _try_end(
    text: str,
    start: int,
    end: int,
    freq: List[int],
    distinct: int,
    tracker: BestTracker,
    trace: Optional[TraceLog],
) -> None:
    """One call of the inner scan: exactly **one stack frame per character**.

    The body is written with a single exit point (no early ``return``) so that
    the trace hook does not need a second function per level.  That is not
    pedantry: an extra frame per character halves the string length this can
    handle before CPython's recursion limit bites (it drops from ~996
    characters to ~497, which ``tests/test_recursion.py`` measures).
    """
    leave = None
    if trace is not None:
        trace.enter("TryEnd", start=start, end=end)

        def leave() -> None:  # noqa: F811 - closes over trace/tracker on purpose
            trace.exit("TryEnd", result=(tracker.length, tracker.strings()))

    if end < len(text):
        index = ord(text[end]) - _A  # normalize() already rejected non-letters
        if freq[index] == 0:
            distinct += 1
        freq[index] += 1

        if distinct <= 2:
            # A third letter would make `distinct` 3; we simply do not recurse,
            # exactly like the original's `if distinct > 2: return`.
            if distinct == 2 and equal_pair(freq):
                tracker.consider_span(text, start, end)
            # freq[:] -- the copy is the price of not having to undo anything.
            _try_end(text, start, end + 1, freq[:], distinct, tracker, trace)

    if leave is not None:
        leave()


def recursive_shared_freq(
    s: Optional[str],
    *,
    casefold: bool = True,
    trace: Optional[TraceLog] = None,
) -> Tuple[int, List[str]]:
    """The same search with one frequency table, mutated and un-mutated.

    >>> recursive_shared_freq("aabbb") == recursive("aabbb")
    True
    """
    text = normalize(s, casefold=casefold)
    return recursive_shared_freq_normalized(text)


def recursive_shared_freq_normalized(text: str) -> Tuple[int, List[str]]:
    """The core of :func:`recursive_shared_freq`, with ``text`` already validated."""
    tracker = BestTracker()
    for start in range(len(text)):
        _walk(text, start, start, [0] * 26, 0, tracker)
    return tracker.result()


def _walk(
    text: str,
    start: int,
    end: int,
    freq: List[int],
    distinct: int,
    tracker: BestTracker,
) -> None:
    if end == len(text):
        return

    index = ord(text[end]) - _A
    is_new_letter = freq[index] == 0
    freq[index] += 1

    if is_new_letter and distinct == 2:
        freq[index] -= 1  # undo before leaving: the caller's table must be intact
        return

    if is_new_letter:
        distinct += 1

    if distinct == 2 and equal_pair(freq):
        tracker.consider_span(text, start, end)

    _walk(text, start, end + 1, freq, distinct, tracker)

    freq[index] -= 1  # undo: this is the backtracking step


def recursive_deep(
    s: Optional[str],
    *,
    casefold: bool = True,
    stack_mb: int = 512,
) -> Tuple[int, List[str]]:
    """Run :func:`recursive` with a big stack and a raised recursion limit.

    Refusing to recurse deeper than 1000 characters is a *Python runtime
    configuration*, not an algorithmic limitation; :func:`~algorithms.support.run_deep`
    shows the supported way to lift it.

    >>> recursive_deep("aabbb")
    (4, ['aabb'])
    """
    return run_deep(recursive, s, casefold=casefold, stack_mb=stack_mb)


def recursive_depth(s: Optional[str], *, casefold: bool = True) -> int:
    """Deepest call depth :func:`recursive` reaches on this input.

    Used by the tests and by the table in ``docs/03-recursion-vs-iteration.md``
    to show that the depth is ``longest scanned window + 2`` frames, not the
    length of the string.
    """
    text = normalize(s, casefold=casefold)
    deepest = {"value": 0}

    def measure(start: int, end: int, freq: List[int], distinct: int, tracker: BestTracker,
                depth: int) -> None:
        deepest["value"] = max(deepest["value"], depth)
        if end == len(text):
            return
        index = ord(text[end]) - _A
        if freq[index] == 0:
            distinct += 1
        freq[index] += 1
        if distinct > 2:
            return
        if distinct == 2 and equal_pair(freq):
            tracker.consider_span(text, start, end)
        measure(start, end + 1, freq[:], distinct, tracker, depth + 1)

    for start in range(len(text)):
        measure(start, start, [0] * 26, 0, BestTracker(), 1)
    return deepest["value"]
