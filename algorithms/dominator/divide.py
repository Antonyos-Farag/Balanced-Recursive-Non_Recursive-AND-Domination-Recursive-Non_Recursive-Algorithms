"""Divide & conquer dominator: halve the problem, keep two candidates.

The halving lemma
-----------------
If ``x`` dominates ``a[lo..hi]`` (more than half of it), then ``x`` dominates
**at least one of the two halves** ``a[lo..mid]`` and ``a[mid+1..hi]``.

Proof.  Suppose not: then ``x`` occurs at most ``len1/2`` times in the left half
and at most ``len2/2`` times in the right half (using integer division), so
altogether at most ``len1/2 + len2/2 <= (len1 + len2)/2`` times -- not more than
half, contradicting that ``x`` dominates.  (The last step is where the two
floor divisions are absorbed: for any two integers, ``floor(p/2) + floor(q/2) <=
floor((p+q)/2)``.)

The algorithm
-------------
Ask each half for its dominator.  If a half has no dominator its answer is
"nothing", and:
* both halves "nothing" -> the whole cannot have one either (the lemma);
* otherwise count each surviving candidate over the whole range and keep the one
  that really is a majority.

The invariant is strong: this function returns the dominator of the range *if
one exists*, and "nothing" otherwise.  Every candidate it hands back has been
counted over the range it claims to dominate, so the answer is never a guess --
compare that with Boyer-Moore, whose candidate must be verified by the caller.

Cost
----
Two counts of at most the range size per node, O(log n) levels, so O(n log n)
element comparisons -- worse than Boyer-Moore's O(n), but it is the natural way
to answer the question "what does a dominator have to do with halves?", and it
parallelises trivially: the two recursive calls are independent.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from ..tracing import TraceLog
from .result import Dominator

__all__ = ["divide_and_conquer", "majority_of_range"]

# A module-private "nothing" marker.  It never escapes this file, which is why
# no caller of this library ever has to reason about sentinel values: the public
# API speaks in Dominator objects and None.
_NOTHING = object()


def _count(a: Sequence[Any], value: Any, lo: int, hi: int) -> int:
    """How many times ``value`` occurs in ``a[lo..hi]`` (inclusive)."""
    total = 0
    for index in range(lo, hi + 1):
        if a[index] == value:
            total += 1
    return total


def majority_of_range(
    a: Sequence[Any],
    lo: int,
    hi: int,
    *,
    trace: Optional[TraceLog] = None,
) -> Any:
    """The dominator of ``a[lo..hi]``, or ``_NOTHING`` when there is none.

    Kept public because the tests and ``docs/02-dominator.md`` want to look at
    subranges; its sentinel is private on purpose.
    """
    if trace is None:
        return _majority_core(a, lo, hi, None)

    trace.enter("majority", lo=lo, hi=hi)
    try:
        answer = _majority_core(a, lo, hi, trace)
    finally:
        trace.exit("majority", result="-" if answer is _NOTHING else answer)
    return answer


def _majority_core(
    a: Sequence[Any],
    lo: int,
    hi: int,
    trace: Optional[TraceLog],
) -> Any:
    """The recursion itself; :func:`majority_of_range` adds the trace bookkeeping."""
    if hi < lo:
        return _NOTHING
    if lo == hi:
        return a[lo]

    mid = (lo + hi) // 2
    left = majority_of_range(a, lo, mid, trace=trace)
    right = majority_of_range(a, mid + 1, hi, trace=trace)

    size = hi - lo + 1

    # A candidate is only accepted after it is counted over the whole range, so
    # what comes back out is a fact, not a hint.
    if left is not _NOTHING:
        left_count = _count(a, left, lo, hi)
        if trace is not None:
            trace.event("count", value=left, lo=lo, hi=hi, count=left_count, size=size)
        if left_count > size // 2:
            return left

    if right is not _NOTHING:
        right_count = _count(a, right, lo, hi)
        if trace is not None:
            trace.event("count", value=right, lo=lo, hi=hi, count=right_count, size=size)
        if right_count > size // 2:
            return right

    # If both halves had nothing, neither candidate passes the count, and the
    # halving lemma says the range has no dominator -- we fall through to
    # _NOTHING, which is the honest answer.
    return _NOTHING


def divide_and_conquer(
    a: Sequence[Any], *, trace: Optional[TraceLog] = None
) -> Optional[Dominator]:
    """Dominate ``a`` by halving, in O(n log n) time and O(log n) stack.

    >>> divide_and_conquer([3, 1, 3, 2, 3, 4, 3, 3])
    Dominator(value=3, indices=(0, 2, 4, 6, 7))
    >>> divide_and_conquer([1, 2, 3, 4]) is None
    True
    >>> divide_and_conquer([]) is None
    True
    >>> divide_and_conquer([None, None, 1])   # works, unlike the submission
    Dominator(value=None, indices=(0, 1))
    """
    n = len(a)
    if n == 0:
        return None

    candidate = majority_of_range(a, 0, n - 1, trace=trace)
    if candidate is _NOTHING:
        return None

    # The recursive search already counted the candidate inside the range it
    # came from; the indices have to be collected once, at the top.
    indices: List[int] = [index for index in range(n) if a[index] == candidate]
    if len(indices) > n // 2:
        return Dominator(candidate, tuple(indices))
    return None
