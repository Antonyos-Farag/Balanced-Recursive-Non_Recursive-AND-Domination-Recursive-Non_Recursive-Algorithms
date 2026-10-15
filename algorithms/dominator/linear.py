"""Two more dominator strategies, and the "give me any index" variant.

``index_cache``
    One pass over the array, remembering every index of every value in a
    dictionary, then a size check.  O(n) time and O(n) extra space -- the honest
    baseline.  It is also the fastest option in practice for the workloads in
    ``docs/05-complexity-lab.md``: one pass, no second scan, no comparisons
    beyond the dictionary hashing.  It requires the values to be hashable, which
    is the price of the dictionary.

``sort_and_pick_middle``
    Sort the array and look at the middle element.  Why the middle?  A dominator
    occupies more than half of the sorted array, so its block of copies is
    longer than half the array and *must* contain the index ``n // 2``: if the
    block started after the middle it would need more room than exists to its
    right, and if it ended before the middle it would need more room to its
    left.  Either way the block covers ``n // 2``.  Then verify by counting.

``any_index``
    The variant most exercise sheets actually ask for ("return any index of the
    dominator, or -1").  It reuses Boyer-Moore and stops at the first index of
    the verified dominator.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .result import Dominator
from .vote import boyer_moore

__all__ = ["any_index", "index_cache", "sort_and_pick_middle"]


def index_cache(a: Sequence[Any]) -> Optional[Dominator]:
    """Collect indices per value in one pass (values must be hashable).

    >>> index_cache("aabaa")
    Dominator(value='a', indices=(0, 1, 3, 4))
    >>> index_cache([1, 2, 3]) is None
    True
    """
    n = len(a)
    if n == 0:
        return None

    seen: Dict[Any, List[int]] = {}
    for index in range(n):
        seen.setdefault(a[index], []).append(index)

    for value, indices in seen.items():
        if len(indices) > n // 2:
            return Dominator(value, tuple(indices))
    return None


def sort_and_pick_middle(a: Sequence[Any]) -> Optional[Dominator]:
    """Sort, take the middle element as the only possible dominator, verify.

    >>> sort_and_pick_middle([3, 1, 3, 2, 3, 4, 3, 3])
    Dominator(value=3, indices=(0, 2, 4, 6, 7))
    >>> sort_and_pick_middle([1, 2, 3, 4]) is None
    True
    """
    n = len(a)
    if n == 0:
        return None

    ordered = sorted(a)  # needs comparable values
    candidate = ordered[n // 2]

    indices = tuple(index for index in range(n) if a[index] == candidate)
    if len(indices) > n // 2:
        return Dominator(candidate, indices)
    return None


def any_index(a: Sequence[Any]) -> int:
    """Any index of the dominator, or ``-1`` if there is none.

    This is the shape most exercise sheets ask for.  ``-1`` is a safe "no
    answer" marker here because indices are non-negative -- the danger is only
    when a *value* is used as its own marker.

    >>> any_index([3, 1, 3, 2, 3, 4, 3, 3])
    0
    >>> any_index([1, 2, 3])
    -1
    """
    dominator = boyer_moore(a)
    if dominator is None:
        return -1
    return dominator.indices[0]
