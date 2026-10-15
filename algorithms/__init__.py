"""Educational reference implementations for two classic problems.

The repository studies four programs, all built from the same assignment:

    +------------------+---------------------+--------------------------+
    |                  | non-recursive       | recursive                |
    +==================+=====================+==========================+
    | balanced string  | double for-loop     | TryStart / TryEnd walk   |
    | dominator        | Boyer-Moore vote    | divide & conquer         |
    +------------------+---------------------+--------------------------+

Sub-packages
------------
``algorithms.original``
    The four programs *exactly as originally submitted* (plus a
    ``__main__`` guard so they can be imported).  Frozen on purpose: this is
    the artifact under study, bugs included.
``algorithms.balanced``
    Balanced substrings: brute force, recursive, and an asymptotically
    better pair-scan algorithm.
``algorithms.dominator``
    Dominators (strict majority elements): Boyer-Moore, divide & conquer,
    and a one-pass index cache.
``algorithms.tracing``
    Small helpers that render call trees, vote walks and frequency tables as
    ASCII, so the algorithms can be *watched* instead of guessed at.

Every claim made in ``docs/`` is backed by an executable test in ``tests/``.
"""

from __future__ import annotations

__all__ = [
    "balanced",
    "dominator",
    "original",
    "tracing",
]

__version__ = "1.0.0"
