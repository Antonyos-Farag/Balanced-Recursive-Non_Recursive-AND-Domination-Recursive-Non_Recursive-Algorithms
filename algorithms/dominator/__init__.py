"""Dominators: the element that appears strictly more than half the time.

What is a dominator?
--------------------
An element ``d`` **dominates** a sequence ``a`` when it appears strictly more
than ``len(a) / 2`` times.  (Some sources say "majority element"; the name
"dominator" comes from a well-known exercise where the answer is reported as the
list of indices at which the dominator occurs.)  Two facts make the whole topic
tractable:

* **At most one value can dominate.**  If ``x`` and ``y`` each occurred more
  than ``n/2`` times they would together occur more than ``n`` times.  So "find
  the dominator" is a *search* problem, never a "which one" problem.
* **A candidate can be found in one pass with O(1) memory** (Boyer-Moore), but
  that candidate must then be verified, because the vote can be wrong.

The four implementations here
-----------------------------
=========================  ============  =====================================
function                   complexity    idea
=========================  ============  =====================================
``boyer_moore``            O(n) time     cancel pairs of different values
                           O(1) space
``divide_and_conquer``     O(n log n)    a dominator dominates one half
``index_cache``            O(n) time,    dictionary of value -> indices
                           O(n) space
``sort_and_pick_middle``   O(n log n)    in sorted order the dominator sits
                                         in the middle
=========================  ============  =====================================

The contract
------------
Every function here takes any sequence and returns either

* a :class:`Dominator` -- the value **and** every index it occupies, or
* ``None`` -- when nothing dominates.

That is the whole contract, and it is deliberately unfussy: ``None`` is the "no
answer" case, and it can never be confused with an answer because the answer is
always a :class:`Dominator` object, never a bare value.

This is the part of the assignment the original programs got wrong.  The
non-recursive one signalled "no dominator" with ``-1`` (fine) while the
recursive one signalled it with an empty list *and* used ``None`` as its
internal "nothing" marker -- so it cannot handle an array that contains
``None``.  Both are documented and reproduced in ``docs/04-bug-hunt.md``
(bugs B8-B14); ``algorithms/original/adapters.py`` shows how to wrap them so
they can take part in a comparison without pretending they were fine.

>>> from algorithms import dominator
>>> dominator.boyer_moore([3, 1, 3, 2, 3, 4, 3, 3])
Dominator(value=3, indices=(0, 2, 4, 6, 7))
>>> dominator.boyer_moore([1, 2, 3]) is None
True
"""

from __future__ import annotations

from typing import Callable, Dict

from .result import NO_DOMINATOR, Dominator
from .vote import (
    VoteStep,
    boyer_moore,
    candidate_or_none,
    vote_steps,
    walk_votes,
)
from .linear import any_index, index_cache, sort_and_pick_middle
from .divide import divide_and_conquer, majority_of_range

__all__ = [
    "Dominator",
    "IMPLEMENTATIONS",
    "NO_DOMINATOR",
    "VoteStep",
    "any_index",
    "boyer_moore",
    "candidate_or_none",
    "divide_and_conquer",
    "index_cache",
    "majority_of_range",
    "sort_and_pick_middle",
    "vote_steps",
    "walk_votes",
]

#: Every dominator implementation under the shared contract, by name.
IMPLEMENTATIONS: Dict[str, Callable[..., object]] = {
    "boyer_moore": boyer_moore,
    "divide_and_conquer": divide_and_conquer,
    "index_cache": index_cache,
    "sort_and_pick_middle": sort_and_pick_middle,
}
