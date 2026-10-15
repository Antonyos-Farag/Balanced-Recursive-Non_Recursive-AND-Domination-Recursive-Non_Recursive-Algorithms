"""The four submitted programs, archived verbatim.

Nothing inside this package was "fixed".  It is the control group: the code
you read in the assignment, kept byte-comparable so that every bug the
documentation describes can be reproduced by running the *original*.

The only edit is a ``if __name__ == "__main__":`` guard around the
interactive driver code, because a module that calls ``input()`` at import
time cannot be tested, imported or reused.  (That guard is itself fix #19 in
``docs/04-bug-hunt.md``.)

Import them like this::

    from algorithms.original import balanced_iterative as bi

    bi.LBS_all_longest("abab")     # -> (4, ['abab'])
"""

from __future__ import annotations

__all__ = [
    "balanced_iterative",
    "balanced_recursive",
    "dominator_iterative",
    "dominator_recursive",
]
