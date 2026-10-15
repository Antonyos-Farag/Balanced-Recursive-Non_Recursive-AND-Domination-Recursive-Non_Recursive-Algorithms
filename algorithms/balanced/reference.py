"""The obvious solution: try everything, check it, keep the best.

This module is the **oracle**.  It is not clever, it is not fast, and that is
the point: when four different algorithms disagree, you need one implementation
whose correctness you can see at a glance and argue about in one sentence.

    every start x every end -> take the substring -> is it balanced?

Time  O(n^3)  -- O(n^2) substrings, and each check walks the substring.
Space O(n)    -- the substring being checked, plus the answers.

Nothing in the rest of the repository is allowed to "fix" its behaviour: if a
faster algorithm disagrees with this one, the faster algorithm is wrong.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .core import BestTracker, is_balanced, normalize

__all__ = ["reference"]


def reference(s: Optional[str], *, casefold: bool = True) -> Tuple[int, List[str]]:
    """Longest balanced substring, computed by brute force over all substrings.

    >>> reference("aabbb")
    (4, ['aabb'])
    >>> reference("aabbc")
    (4, ['aabb'])
    >>> reference("abcabc")
    (2, ['ab', 'bc', 'ca'])
    >>> reference("aaaa")
    (0, [])
    """
    text = normalize(s, casefold=casefold)
    return reference_normalized(text)


def reference_normalized(text: str) -> Tuple[int, List[str]]:
    """Same algorithm, assuming ``text`` is already normalised."""
    tracker = BestTracker()
    n = len(text)
    for start in range(n):
        for end in range(start + 1, n + 1):
            window = text[start:end]
            # No shortcuts.  An earlier draft of this file read
            # `if len(window) > tracker.length and is_balanced(window)`, which
            # looks like a harmless speed-up and silently drops every
            # *additional* substring that ties with the best one -- it answered
            # (2, ['ab']) for "abcabc" instead of (2, ['ab', 'bc', 'ca']).
            # An oracle that is clever is not an oracle.  (The exhaustive test
            # in tests/test_balanced_implementations.py is what caught it; see
            # docs/04-bug-hunt.md, "the oracle that wasn't".)
            if is_balanced(window):
                tracker.consider(window)  # the window is already built: we counted it
    return tracker.result()
