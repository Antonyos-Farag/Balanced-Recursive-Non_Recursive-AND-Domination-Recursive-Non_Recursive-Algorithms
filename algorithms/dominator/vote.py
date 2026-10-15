"""Boyer-Moore majority vote: cancel unlike pairs, verify, then collect.

The vote, in one sentence
-------------------------
Walk the array keeping a *candidate* and a *count*.  When the count is zero,
adopt the current element as the candidate with count 1.  When the current
element equals the candidate, increment; otherwise decrement (the two "cancel
each other out").

Why it works
------------
Every cancellation removes two *different* elements from consideration.  If some
value really does occupy more than half the array, it cannot be cancelled away
completely: pair it up against anything else and at least one copy of it is
always left standing.  Formally, the candidate after the walk is a dominator
whenever a dominator exists -- but nothing more.

Why you must verify
-------------------
The vote gives no guarantee at all when there is no dominator.  ``[1, 2, 3]``
ends with candidate ``3`` and count ``1``, which is not a majority of anything.
That is why every correct implementation spends a second pass counting the
candidate's real occurrences.  A one-pass-only "optimisation" is the classic
way to get this exercise wrong, and it is the first thing worth testing.

Cost: two passes, O(n) time, O(1) extra memory (plus the returned indices).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .result import Dominator

__all__ = [
    "VoteStep",
    "boyer_moore",
    "candidate_or_none",
    "vote_steps",
    "walk_votes",
]

# A private sentinel, so that "no candidate at all" can never be confused with
# "the candidate happens to be the value None".  The submitted program used
# None for both, which is bug B12 in docs/04-bug-hunt.md.
_NOTHING = object()


@dataclass(frozen=True)
class VoteStep:
    """One step of the vote, kept for teaching and for the trace tables."""

    index: int
    value: Any
    action: str  # "elect" | "support" | "cancel"
    candidate: Any
    count: int
    final_count: int = 0
    size: int = 0


def candidate_or_none(a: Sequence[Any]) -> Optional[Any]:
    """The raw vote candidate, or ``None`` for an empty array.

    This helper exists to make a *design* point.  Look how it fails::

        >>> candidate_or_none([])          # no elements...
        >>> candidate_or_none([None, None])  # ...and this hands back None too

    Both calls print ``None``, but they mean different things: the first has no
    candidate, the second has one and it is the value ``None``.  Returning a
    bare value plus a magic marker cannot express that, which is exactly why the
    public API returns a :class:`Dominator` or ``None`` instead.
    """
    found, value = _vote(a)
    return value if found else None


def _vote(a: Sequence[Any]) -> Tuple[bool, Any]:
    """The vote itself: ``(candidate_found, candidate)``.

    The private boolean is what makes the sentinel problem disappear -- callers
    that stay inside this module never have to guess.
    """
    candidate: Any = _NOTHING
    count = 0
    for index in range(len(a)):
        value = a[index]
        if count == 0:
            candidate = value
            count = 1
        elif value == candidate:
            count += 1
        else:
            count -= 1
    if candidate is _NOTHING:
        return False, None
    return True, candidate


def walk_votes(a: Sequence[Any]) -> List[VoteStep]:
    """Every step of the vote, including the verification pass's total.

    >>> [step.action for step in walk_votes([1, 1, 2, 3])]
    ['elect', 'support', 'cancel', 'cancel']
    """
    steps: List[VoteStep] = []
    candidate: Any = _NOTHING
    count = 0
    for index in range(len(a)):
        value = a[index]
        if count == 0:
            candidate = value
            count = 1
            action = "elect"
        elif value == candidate:
            count += 1
            action = "support"
        else:
            count -= 1
            action = "cancel"
        steps.append(VoteStep(index, value, action, candidate, count))

    final_count = 0
    if candidate is not _NOTHING:
        for index in range(len(a)):
            if a[index] == candidate:
                final_count += 1
        steps = [
            VoteStep(
                step.index,
                step.value,
                step.action,
                step.candidate,
                step.count,
                final_count=final_count,
                size=len(a),
            )
            for step in steps
        ]
    return steps


def vote_steps(a: Sequence[Any]) -> List[Tuple[int, Any, str, Any, int]]:
    """A dependency-free view of :func:`walk_votes`, handy in doctests."""
    return [(s.index, s.value, s.action, s.candidate, s.count) for s in walk_votes(a)]


def boyer_moore(a: Sequence[Any]) -> Optional[Dominator]:
    """Dominate ``a`` with O(n) time and O(1) extra memory.

    >>> boyer_moore([3, 1, 3, 2, 3, 4, 3, 3])
    Dominator(value=3, indices=(0, 2, 4, 6, 7))
    >>> boyer_moore([1, 2, 3, 4]) is None
    True
    >>> boyer_moore([]) is None
    True
    >>> boyer_moore([None, None, 1])          # a dominator that *is* None
    Dominator(value=None, indices=(0, 1))
    """
    n = len(a)
    if n == 0:
        return None

    found, candidate = _vote(a)
    if not found:
        return None

    # Verification pass: the vote is a hint, never a proof.
    indices: List[int] = []
    for index in range(n):
        if a[index] == candidate:
            indices.append(index)

    if len(indices) > n // 2:
        return Dominator(candidate, tuple(indices))
    return None
