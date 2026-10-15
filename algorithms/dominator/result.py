"""The result type for the dominator package.

``Dominator`` exists to make one whole class of bug impossible.

The submitted programs answered the question in three different ways: one
returned a list of indices, another returned a list of indices *or* an empty
list, and a third returned ``-1``.  Whenever "no answer" is expressed by a value
that could also be a real answer (an empty list, ``-1``, ``None``), the caller
has to remember which values are special -- and the value ``None`` is exactly
the kind of thing a caller hands in without thinking about it, which is how the
recursive submission ended up unable to handle an array containing ``None``.

A small immutable result object removes the ambiguity: either you get a
``Dominator``, or you get ``None``.  There is no third case to remember, and
``None`` as a *value* is perfectly fine:

>>> from algorithms.dominator.result import Dominator
>>> Dominator(None, (0, 1))
Dominator(value=None, indices=(0, 1))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

__all__ = ["Dominator"]


@dataclass(frozen=True)
class Dominator:
    """A value that occurs more than half the time, with all of its indices.

    Equality is structural (it is a dataclass), which makes it pleasant in
    tests::

        >>> Dominator(3, (0, 2, 4)) == Dominator(3, (0, 2, 4))
        True
    """

    value: Any
    indices: Tuple[int, ...]

    @property
    def count(self) -> int:
        """How many times the dominator occurs."""
        return len(self.indices)

    def __len__(self) -> int:
        return len(self.indices)

    def __iter__(self):
        return iter(self.indices)

    def percentage(self, total: int) -> float:
        """The share of the sequence the dominator occupies, in percent."""
        if total <= 0:
            raise ValueError("total must be positive")
        return round(100.0 * self.count / total, 2)


#: An explicit alias for the "nothing dominates" case, for callers that prefer
#: naming it over writing ``None``.
NO_DOMINATOR: Optional[Dominator] = None
