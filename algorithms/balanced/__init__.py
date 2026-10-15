"""Balanced substrings, four ways, all agreeing on one contract.

===================  ============  ==========================================
function             complexity    one-line description
===================  ============  ==========================================
``reference``        O(n^3)        try every substring, ask ``is_balanced``
``brute_force``      O(n^2)        repaired double loop, frequency table
``brute_force_incremental``  O(n^2)   the same, with an O(1) balance test
``round_trip``       O(n^2)        the recursion unrolled into loops
``recursive``        O(n^2)        repaired TryStart/TryEnd recursion
``recursive_shared_freq``  O(n^2)   same, one table mutated and undone
``pair_scan``        ~O(n log n)   325 letter pairs + prefix sums
``pair_scan_two_pass``  same       ... copying only the final answers
===================  ============  ==========================================

All of them return ``(length, sorted_list_of_substrings)`` and all of them agree
on every input.  That is not a hope: ``tests/test_balanced_implementations.py``
checks them against each other exhaustively for short strings and randomly for
long ones.

>>> from algorithms import balanced
>>> balanced.reference("aabbc")
(4, ['aabb'])
>>> balanced.pair_scan("aabbc")
(4, ['aabb'])
>>> balanced.recursive("abab")[0]
4
"""

from __future__ import annotations

from typing import Callable, Dict

from .core import (
    BestTracker,
    counts_of,
    equal_pair,
    is_balanced,
    legacy_equal_pair,
    normalize,
)
from .fast import (
    PairReport,
    pair_scan,
    pair_scan_normalized,
    pair_scan_report,
    pair_scan_two_pass,
    pair_scan_two_pass_normalized,
)
from .iterative import (
    brute_force,
    brute_force_incremental,
    brute_force_normalized,
    round_trip,
)
from .recursion import (
    recursive,
    recursive_deep,
    recursive_depth,
    recursive_shared_freq,
)
from .reference import reference, reference_normalized

__all__ = [
    "BestTracker",
    "PairReport",
    "IMPLEMENTATIONS",
    "brute_force",
    "brute_force_incremental",
    "counts_of",
    "equal_pair",
    "is_balanced",
    "legacy_equal_pair",
    "normalize",
    "pair_scan",
    "pair_scan_report",
    "pair_scan_two_pass",
    "recursive",
    "recursive_deep",
    "recursive_depth",
    "recursive_shared_freq",
    "reference",
    "round_trip",
]

#: Every balanced-string implementation under the shared contract, by name.
#: The tools and the tests iterate over this instead of hard-coding names.
IMPLEMENTATIONS: Dict[str, Callable[..., object]] = {
    "reference": reference,
    "brute_force": brute_force,
    "brute_force_incremental": brute_force_incremental,
    "round_trip": round_trip,
    "recursive": recursive,
    "recursive_shared_freq": recursive_shared_freq,
    "pair_scan": pair_scan,
    "pair_scan_two_pass": pair_scan_two_pass,
}
