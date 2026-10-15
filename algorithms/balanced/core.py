"""Shared vocabulary for the balanced-substring programs.

Everything in the balanced-string package agrees on four things.  Getting these
four decisions written down *once* is what makes four different algorithms
comparable at all.

1. What "balanced" means
------------------------
A string is **balanced** when it uses **exactly two distinct characters and each
of them appears the same number of times**.  Examples::

    "ab"      balanced   (a:1, b:1)
    "aabb"    balanced   (a:2, b:2)
    "aabbc"   not        (three distinct characters)
    "aaaa"    not        (one distinct character)
    "aaabb"   not        (a:3, b:2, counts differ)
    ""        not        (no characters at all; the assignment returns length 0)

Notice how *unnatural* that is compared with the usual "longest substring with
at most two distinct characters": balance is **not** monotone, so the usual
sliding-window trick does not apply.  ``docs/01-balanced-strings.md`` shows a
counterexample.  This is the single most important thing to understand about
this problem, because it is why the "obvious" O(n) solution does not exist.

2. What counts as input
-----------------------
Any ASCII letter; case is folded to lower case by default (``casefold=False``
makes the functions strict about lower case).  Anything else -- digits,
spaces, punctuation, non-ASCII letters such as ``'é'`` -- raises ``ValueError``
instead of being silently ignored.  ``None`` is treated like ``""`` because the
original non-recursive program did that and it is a useful behaviour for a
function that reports "0, nothing found".

The **two archived programs disagree** on both points; that disagreement is
documented and tested in ``docs/04-bug-hunt.md`` (bugs B2 and B5).  Here we
pick one policy and apply it everywhere.

3. What the output means
------------------------
Every implementation returns a pair ``(length, substrings)`` where ``length``
is the length of the longest balanced substring (0 if there is none) and
``substrings`` is the sorted list of *distinct* substrings of that length.
Sorted order is part of the contract: it makes different implementations
directly comparable, whereas the original returned them in the order the loops
happened to find them.

4. Where the work happens
-------------------------
Each module exposes a ``*_normalized`` function that trusts its input.  The
public functions are thin wrappers: normalize first, then run the core.  That
split is what lets ``docs/05-complexity-lab.md`` feed the algorithms a
:class:`~algorithms.support.ReadCounter` and count character reads without the
normalization pass polluting the measurement.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "ALPHABET_SIZE",
    "BestTracker",
    "counts_of",
    "equal_pair",
    "freq_summary",
    "is_balanced",
    "legacy_equal_pair",
    "normalize",
]

ALPHABET_SIZE = 26
_A = ord("a")


def normalize(s: Optional[str], *, casefold: bool = True) -> str:
    """Validate and normalise a balanced-string input.

    >>> normalize("AaBb")
    'aabb'
    >>> normalize("AaBb", casefold=False)
    Traceback (most recent call last):
        ...
    ValueError: only ASCII letters are allowed; found 'A' at index 0
    >>> normalize(None)
    ''
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        raise TypeError(f"expected str or None, got {type(s).__name__}")
    out: List[str] = []
    for index, ch in enumerate(s):
        if "a" <= ch <= "z":
            out.append(ch)
        elif casefold and "A" <= ch <= "Z":
            out.append(ch.lower())
        else:
            raise ValueError(
                f"only ASCII letters are allowed; found {ch!r} at index {index}"
            )
    return "".join(out)


def counts_of(text: str) -> Dict[str, int]:
    """Character counts, e.g. ``counts_of('aab')`` -> ``{'a': 2, 'b': 1}``."""
    counts: Dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    return counts


def is_balanced(text: str) -> bool:
    """True iff ``text`` has exactly two distinct characters, equally often.

    This is the definition, written straight from the problem statement.  It is
    deliberately slow and obvious: it is the **oracle** the other
    implementations are checked against.
    """
    counts = counts_of(text)
    if len(counts) != 2:
        return False
    first, second = counts.values()
    return first == second


def equal_pair(freq: Sequence[int]) -> bool:
    """True iff a 26-slot frequency table holds exactly two equal non-zero counts.

    This is the hot inner test of the O(n^2) algorithm, so it avoids building a
    list: it walks the 26 slots once, remembers the first two values it sees and
    rejects a third one immediately.  (Zero means "unused", because counts are
    never negative here.)

    >>> equal_pair([2, 2] + [0] * 24)
    True
    >>> equal_pair([2, 3] + [0] * 24)
    False
    >>> equal_pair([2, 2, 1] + [0] * 23)
    False
    """
    first = 0
    second = 0
    for value in freq:
        if value:
            if first == 0:
                first = value
            elif second == 0:
                second = value
            else:
                return False
    return first != 0 and first == second


def legacy_equal_pair(freq: Sequence[int]) -> bool:
    """The frequency test exactly as the two archived programs wrote it.

    Kept as a museum piece, because it is subtly weaker than
    :func:`equal_pair`: it only looks at the first two non-zero slots, so it
    answers ``True`` for a table that holds **three** different counts as long
    as the first two happen to match.  The archived programs never notice,
    because an independently maintained ``distinct`` counter short-circuits
    that case first -- which is precisely the kind of double guard that turns
    into a bug the day somebody deletes one of the two halves.

    >>> legacy_equal_pair([2, 2, 1] + [0] * 23)   # three letters! still True
    True
    >>> equal_pair([2, 2, 1] + [0] * 23)          # the repaired version
    False
    """
    first_freq = -1
    second_freq = -1
    for f in freq:
        if f > 0:
            if first_freq == -1:
                first_freq = f
            elif second_freq == -1:
                second_freq = f
    return first_freq != -1 and second_freq != -1 and first_freq == second_freq


def freq_summary(freq: Sequence[int]) -> str:
    """Human-readable non-zero slots, e.g. ``'a:2 b:1'`` (used by traces)."""
    parts = [
        f"{chr(_A + index)}:{value}"
        for index, value in enumerate(freq)
        if value
    ]
    return " ".join(parts) if parts else "-"


class BestTracker:
    """The accumulator that both scans thread through their recursion.

    Keeping the "best so far" in one tiny object instead of in two arguments is
    what makes the recursive and the loop versions easy to compare: the
    recursion keeps its *memory* in this object and never has to return a pair
    of values up the call chain.

    >>> tracker = BestTracker()
    >>> tracker.consider("ab"); tracker.consider("aabb"); tracker.consider("bbaa")
    >>> tracker.result()
    (4, ['aabb', 'bbaa'])
    """

    __slots__ = ("length", "_seen")

    def __init__(self) -> None:
        self.length = 0
        self._seen: set = set()

    def consider(self, candidate: str) -> None:
        """Offer a balanced substring; keep it only if it ties or beats the best."""
        size = len(candidate)
        if size > self.length:
            self.length = size
            self._seen = {candidate}
        elif size == self.length and size:
            self._seen.add(candidate)

    def consider_span(self, text: str, start: int, end: int) -> None:
        """Offer ``text[start:end + 1]`` **without building it unless it can win**.

        This one-line guard is worth more than it looks.  On an input like
        ``"abababab..."`` there are ``Theta(n^2)`` balanced windows, and slicing
        each of them costs ``Theta(length)``, which turns an O(n^2) *scan* into a
        Theta(n^3) *program*.  Nothing can win unless it is at least as long as
        the current best, so the slice -- and its cost -- can wait.

        Measured on ``"ab" * 250`` (500 characters) for ``brute_force``, counting
        element reads: **31,813,500 before the guard, 188,000 after it** -- and of
        those 188,000, 125,250 are the scan itself (the unavoidable n^2 / 2) and
        62,750 are the copies of the answers as they improve.  ``docs/05`` has the
        tables.
        """
        size = end - start + 1
        if size < self.length or size < 1:
            return
        self.consider(text[start : end + 1])

    def strings(self) -> List[str]:
        """The substrings kept so far, sorted (all of them have ``length``)."""
        return sorted(self._seen)

    def merge(self, other: "BestTracker") -> None:
        """Fold another tracker in.

        Only ``other``'s *longest* candidates can matter globally, and offering
        them one by one to :meth:`consider` promotes or ignores them correctly.
        """
        for candidate in other.strings():
            self.consider(candidate)

    def result(self) -> Tuple[int, List[str]]:
        """``(length, sorted substrings)`` -- the package's return contract."""
        return self.length, sorted(self._seen)

    def __len__(self) -> int:
        return len(self._seen)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"BestTracker(length={self.length}, found={sorted(self._seen)})"
