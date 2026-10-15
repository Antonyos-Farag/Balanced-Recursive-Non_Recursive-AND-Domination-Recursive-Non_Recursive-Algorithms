"""Adapters: make the archived submissions speak the modern contract.

Why bother?
-----------
The four submitted programs cannot be compared directly, because they answer the
same question in three different shapes:

=========================  ===========================  =========================
program                    no dominator               result
=========================  ===========================  =========================
``dominator``              ``-1``                     list of indices
``find_dominator_indices`` ``[]``                     list of indices
=========================  ===========================  =========================

A test that compares a list with ``-1`` compares nothing at all.  So the
archive stays frozen and this module wraps it: an **adapter** converts the old
output shape into the new contract without touching the old code.

The adverb matters: these adapters normalise the *output shape* only.  They do
not repair behaviour.  ``legacy_iterative`` still refuses upper-case input, and
``legacy_divide_and_conquer`` still cannot see a dominator whose value is
``None`` -- that is the point.  Hiding those differences would hide the bugs.

>>> from algorithms.original import adapters
>>> adapters.legacy_dominator([3, 1, 3, 2, 3, 4, 3, 3])
Dominator(value=3, indices=(0, 2, 4, 6, 7))
>>> adapters.legacy_dominator([1, 2, 3]) is None
True
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple

from ..dominator.result import Dominator
from . import balanced_iterative as _bi
from . import balanced_recursive as _br
from . import dominator_iterative as _di
from . import dominator_recursive as _dr

__all__ = [
    "legacy_iterative",
    "legacy_recursive",
    "legacy_dominator",
    "legacy_divide_and_conquer",
    "LEGACY_BALANCED",
    "LEGACY_DOMINATOR",
]


def _sorted_result(length: int, substrings: Sequence[str]) -> Tuple[int, List[str]]:
    """The submitted programs returned discovery order; the contract is sorted."""
    return length, sorted(substrings)


def legacy_iterative(s: Optional[str]) -> Tuple[int, List[str]]:
    """``LBS_all_longest``, output normalised.

    Input policy is left exactly as submitted: anything that is not ``a``-``z``
    prints an error and yields ``(0, [])``.
    """
    length, substrings = _bi.LBS_all_longest(s)
    return _sorted_result(length, substrings)


def legacy_recursive(s: Optional[str]) -> Tuple[int, List[str]]:
    """``LBS``, output normalised.

    Input policy is left as submitted: the string is lower-cased and scanning
    stops at the first non-letter instead of complaining.
    """
    length, substrings = _br.LBS(s)
    return _sorted_result(length, substrings)


def legacy_dominator(a: Sequence[Any]) -> Optional[Dominator]:
    """``dominator`` (Boyer-Moore style), ``-1`` converted to ``None``."""
    result = _di.dominator(a)
    if result == -1:
        return None
    indices = tuple(result)
    return Dominator(a[indices[0]], indices)


def legacy_divide_and_conquer(a: Sequence[Any]) -> Optional[Dominator]:
    """``find_dominator_indices``, empty list converted to ``None``.

    Careful: this is the adapter that cannot distinguish "no dominator" from "a
    dominator whose value is ``None``" -- because the function it wraps cannot
    either.  See bug B12.
    """
    indices = _dr.find_dominator_indices(list(a))
    if not indices:
        return None
    indices = tuple(indices)
    return Dominator(a[indices[0]], indices)


#: The archived balanced-string programs under the shared contract.
LEGACY_BALANCED = {
    "legacy_iterative": legacy_iterative,
    "legacy_recursive": legacy_recursive,
}

#: The archived dominator programs under the shared contract.
LEGACY_DOMINATOR = {
    "legacy_dominator": legacy_dominator,
    "legacy_divide_and_conquer": legacy_divide_and_conquer,
}
