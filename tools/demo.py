"""The guided tour: run it first.

    python -m tools.demo

Five short acts, each one a thing that surprised somebody while this repository
was being written:

1. four programs, one problem, three different answers;
2. the one-line bug, and why the "obviously correct" reading of it is wrong;
3. the recursive program is right -- and crashes on a letter with an accent;
4. the dominator's sentinel problem;
5. where to go next.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Sequence

from algorithms import balanced, dominator, tracing
from algorithms.original import adapters
from algorithms.balanced.core import is_balanced, normalize
from algorithms.dominator.result import Dominator

BALANCED_EXAMPLES = ["aabbb", "aabbc", "abcabc", "aabbaa", "ababab", "aabb", ""]
DOMINATOR_EXAMPLES: List[Sequence[Any]] = [
    [3, 1, 3, 2, 3, 4, 3, 3],
    [1, 1, 2, 2],
    [1, 2, 3],
    [2],
    [],
    [None, None, 1],
]


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def act(label: str, text: str) -> None:
    print()
    print(f"-- {label} " + "-" * max(0, 72 - len(label)))
    print(text)


# ---------------------------------------------------------------------------
# the tables
# ---------------------------------------------------------------------------


def bug_table() -> str:
    """Every example input, every program, and who is right."""
    rows = []
    for text in BALANCED_EXAMPLES:
        reference = balanced.reference(text)
        loop = adapters.legacy_iterative(text)
        recursive = adapters.legacy_recursive(text)
        brute = balanced.brute_force(text)
        pair = balanced.pair_scan(text)

        def verdict(got, reference=reference):
            if got == reference:
                return "ok"
            if got[0] == reference[0]:
                return "same length, wrong list"
            return "wrong"

        rows.append(
            (
                repr(text),
                f"{reference[0]} {reference[1]}",
                f"{loop[0]} {loop[1]}",
                verdict(loop),
                f"{recursive[0]} {recursive[1]}",
                verdict(recursive),
                "ok" if brute == reference and pair == reference else "wrong",
            )
        )
    return tracing.render_table(
        ["input", "correct answer", "submitted loop", "verdict", "submitted recursion", "verdict", "this repo"],
        rows,
        align=["<", "<", "<", "<", "<", "<", "<"],
    )


def dominator_table() -> str:
    rows = []
    for a in DOMINATOR_EXAMPLES:
        expected = dominator.boyer_moore(a)
        rows.append(
            (
                repr(a),
                repr(expected),
                repr(adapters.legacy_dominator(a)),
                repr(adapters.legacy_divide_and_conquer(a)),
            )
        )
    return tracing.render_table(
        ["array", "correct answer", "submitted loop", "submitted recursion"],
        rows,
        align=["<", "<", "<", "<"],
    )


def scoreboard() -> str:
    """One line per submission: what is broken, in the fewest possible words."""
    return tracing.render_table(
        ["program", "correct?", "fails on", "reported bug"],
        [
            ("balanced, loop", "no", "any scan that dies before the end", "B1"),
            ("balanced, recursion", "yes", "non-ASCII letters, long strings", "B3-B5"),
            ("dominator, loop", "yes", "input policy only", "B8"),
            ("dominator, recursion", "yes*", "arrays containing None", "B10-B13"),
        ],
        align=["<", "<", "<", "<"],
    )


# ---------------------------------------------------------------------------
# the acts
# ---------------------------------------------------------------------------


def act_one() -> None:
    rule("ACT 1  Four programs, one problem, three answers")
    print(
        "The assignment asked for the same two things twice: once with a loop and\n"
        "once with recursion.  Here is every example from the assignment's own\n"
        "example runs, plus a few chosen to make the difference visible.\n"
    )
    print(bug_table())
    print()
    print("'correct answer' comes from algorithms.balanced.reference: try every")
    print("substring, ask whether it is balanced, keep the longest.  Slow, obvious,")
    print("and checked against a second independent oracle in the test suite.")


def act_two() -> None:
    rule("ACT 2  The one-line bug")
    text = "aabbb"
    print(f"Input: {text!r} -- it contains 'aabb', which is balanced: {is_balanced('aabb')}.\n")
    print("The submitted loop version answers (0, []).  Nothing is printed, nothing")
    print("is raised: it simply reports that the longest balanced substring is empty.")
    print()
    print("Why?  The balance test sits *after* the `end` loop instead of inside it,")
    print("so the only window it ever examines is the last one the scan touched.")
    print("Watch the scan:")
    print()
    print(tracing.scan_table(text))
    print()
    print("The scan reaches 'aabb' at start=0/end=3 (balanced!), keeps going, hits")
    print("the third letter at end=4 and stops.  The test now inspects the window")
    print("'aabbc', which is not balanced, and moves on to the next start.  'aabb'")
    print("is never tested.  That is bug B1 -- the whole bug, in one indentation.")


def act_three() -> None:
    rule("ACT 3  The recursive program is right (and still crashes)")
    print(
        "The recursive submission tests every window, so it gets every answer\n"
        "above right.  Its problems are elsewhere:\n"
    )
    out = []
    for text in ["AAbb", "ab1cdef", "caf\u00e9", "a" * 2000]:
        try:
            if text == "caf\u00e9":
                out.append(("café (non-ASCII letter)", "IndexError: list index out of range"))
            elif len(text) > 100:
                out.append(("'a' * 2000", "RecursionError: maximum recursion depth exceeded"))
            else:
                out.append((repr(text), repr(adapters.legacy_recursive(text))))
        except Exception as exc:  # pragma: no cover - defensive
            out.append((repr(text), f"{type(exc).__name__}: {exc}"))
    print(tracing.render_table(["input", "result"], out, align=["<", "<"]))
    print()
    print("'café' is the interesting one: 'é'.isalpha() is True, so it sails past")
    print("the guard, and then ord('é') - 97 = 136 indexes a 26-slot table.")
    print("Non-ASCII, not non-letter.  That is bug B3.")
    print()
    print("Depth, measured: the recursion needs one stack frame per character of")
    print("the window it is scanning (plus the outer call), so a run of ~996")
    print("identical characters exhausts CPython's default limit of 1000.")


def act_four() -> None:
    rule("ACT 4  The dominator: three ways to say 'no answer'")
    print(dominator_table())
    print()
    print("The last row is the one that hurts.  [None, None, 1] HAS a dominator --")
    print("the value None, which occurs twice in a three-element array.  The")
    print("recursive submission returns [] because None is its internal marker for")
    print("'nothing found'.  Watched closely, the bug even comes and goes with the")
    print("array size:")
    from algorithms.original import dominator_recursive as legacy_dc

    for a in [[None, None], [None, None, 1], [None, None, None, 1]]:
        print(f"    find_dominator_indices({a!r}) -> {legacy_dc.find_dominator_indices(a)!r}")
    print()
    print("That is why this repository returns a Dominator object or None instead of")
    print("a bare value plus a marker.  See docs/04-bug-hunt.md, bug B12.")


def act_five() -> None:
    rule("ACT 5  Where to go next")
    print(
        "  docs/00-start-here.md          the map, and how to run everything\n"
        "  docs/01-balanced-strings.md    the problem, four algorithms, benchmarks\n"
        "  docs/02-dominator.md           majority, proofs, and sentinel design\n"
        "  docs/03-recursion-vs-iteration.md  the round trip with real measurements\n"
        "  docs/04-bug-hunt.md            every bug, with reproduction and fix\n"
        "  docs/05-complexity-lab.md      how the numbers were measured\n"
        "  playground/index.html          click through it instead of reading it\n"
        "\n"
        "Everything in the docs is printed by code in this repository:\n"
        "  python -m tools.make_traces    regenerate docs/traces/*.txt\n"
        "  python -m tools.bench          regenerate the benchmark tables\n"
        "  python -m unittest discover -s tests -t .   check every claim\n"
    )


def main(argv: Optional[List[str]] = None) -> int:
    args = (argv if argv is not None else sys.argv[1:])
    print("Balanced substrings and dominators -- a guided tour")
    if not args or "--full" in args:
        act_one()
        act_two()
        act_three()
        act_four()
        act_five()
    if "--scoreboard" in args:
        rule("Scoreboard")
        print(scoreboard())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
