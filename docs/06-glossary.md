# 06 -- Glossary

The vocabulary this repository uses, in the sense it uses it. Entries are
alphabetical; each one says where the term does real work, so you can jump
straight to the chapter that uses it rather than to a dictionary.

---

**accumulator** -- a value that is carried along by a search and updated as it
goes, rather than being passed back up the call chain. Here it is
`BestTracker` (best length + the set of substrings attaining it).
*Where:* [`docs/03`](03-recursion-vs-iteration.md), `algorithms/balanced/core.py`.

**adapter** -- a wrapper that changes a function's *interface* (argument shapes,
return types, error behaviour) without changing its *behaviour*.
`algorithms/original/adapters.py` wraps the archived programs so they can be
compared with the repaired ones. The subtlety, stated in that file: an adapter
must not hide a bug, or the comparison becomes a lie.
*Where:* `adapters.py`, `docs/04`.

**amortised** -- "expensive occasionally, cheap on average per operation". Not
used as a term of praise here: `pair_scan_two_pass` pays `O(n)` extra up front to
avoid `Theta(n^2)` copying later, which is a *trade*, not an amortisation.
*Where:* [`docs/05`](05-complexity-lab.md).

**archive, the** -- `algorithms/original/`: the four submitted programs, kept
byte-for-byte as submitted apart from one added `if __name__ == "__main__":`
guard, with SHA-256 digests in `FROZEN.sha256`. It is evidence, not code to
edit; a failing characterization test means somebody changed history.
*Where:* [`docs/04`](04-bug-hunt.md), `tests/test_original_characterization.py`.

**balanced (substring)** -- in this repository, a string that uses **exactly two
distinct characters, each the same number of times**. `"ab"`, `"aabb"`, `"bbaa"`
are balanced; `"aaaa"`, `"aabbc"`, `"aaabb"` and `""` are not. The definition is
the assignment's, not the more common "at most two distinct characters".
*Where:* [`docs/01`](01-balanced-strings.md), `algorithms/balanced/core.py`.

**Boyer-Moore vote** -- the linear-time majority algorithm: keep a candidate and a
counter; a different value decrements the counter, and at zero the next value
becomes the candidate. It computes a **candidate**, not an answer: the candidate
can be wrong, so a verification pass is mandatory.
*Where:* [`docs/02`](02-dominator.md), `algorithms/dominator/vote.py`.

**break-even point** -- the input size at which a cleverer algorithm overtakes a
simpler one. This repository measures it (the pair scan wins on `"abab..."` from
`n = 10`, and loses by 20x on `"abc...z"` repeated), because "the smarter
algorithm is faster" is false below the break-even and on the wrong shape.
*Where:* [`docs/05`](05-complexity-lab.md).

**characterization test** -- a test that pins down what code *currently does*,
bugs included, so that history cannot be quietly rewritten.
`tests/test_original_characterization.py` is the main one: it asserts that the
loop submission returns `(0, [])` for `"aabbb"`, and that a model of the misplaced
check reproduces it on 20,000 random inputs.
*Where:* [`docs/04`](04-bug-hunt.md), `tests/test_original_characterization.py`.

**constant factor** -- everything Big-O throws away. Here it is often the whole
story: the pair scan examines `4n` characters on random 4-letter text where the
quadratic scan examines `4.3n`, so the asymptotic argument predicts nothing about
which is faster at `n = 1,000`.
*Where:* [`docs/05`](05-complexity-lab.md).

**contract** -- the set of promises a function makes: accepted inputs, return
shape, ordering, error behaviour. Written down once per problem in
`algorithms/balanced/__init__.py` and `algorithms/dominator/__init__.py`, and
enforced by `tests/test_contracts.py`. The archived programs speak three
different dialects for "no answer" (`-1`, `[]`, `(0, [])`).
*Where:* [`docs/01`](01-balanced-strings.md), [`docs/02`](02-dominator.md).

**dead code** -- a statement whose result is never used. `left_count` in the
archived divide & conquer is one, and this repository does not argue about it: a
test parses the file with `ast` and asserts the name is stored once and loaded
zero times.
*Where:* [`docs/04`](04-bug-hunt.md) (B9).

**differential testing** -- running two implementations on the same inputs and
comparing. It turns "I think this is wrong" into a counterexample, and it is the
highest-yield technique in this repository's history: it found both the loop
submission's bug and the first oracle's bug.
*Where:* [`docs/04`](04-bug-hunt.md), `tests/test_balanced_implementations.py`.

**distinct characters** -- the number of *different* characters, counted once
each, regardless of how often they appear. `"aabbc"` has 3 distinct characters
and 5 characters.
*Where:* [`docs/01`](01-balanced-strings.md).

**divide & conquer (for the dominator)** -- split the range, ask each half for its
majority, and count a candidate over the whole range only when it survives. The
halving lemma (a strict majority of a range is a strict majority of at least one
half) is what makes it correct; the counting is `O(n)` per level, so
`O(n log n)` overall.
*Where:* [`docs/02`](02-dominator.md), `algorithms/dominator/divide.py`.

**doctest** -- a code example in a docstring that is *executed*. Used throughout
`algorithms/` and `tools/` so that documented examples cannot rot; the whole lot
runs as part of the suite (`python -m unittest tests.test_doctests`), which is
the only reason to trust an example you did not just run.
*Where:* every module in `algorithms/` and `tools/`.

**dominator** -- an element occurring **strictly more than `n/2`** times
(Codility's name for a strict majority element). At most one can exist; the
repository returns `Dominator(value, indices) | None` rather than an index or a
magic value.
*Where:* [`docs/02`](02-dominator.md), `algorithms/dominator/__init__.py`.

**drift check** -- a test that regenerates a committed artifact and compares it
with the file on disk. `tests/test_docs_traces.py` does this for every trace in
`docs/traces/` except `bench.txt`: if the code changes and the documentation is
not regenerated, the build fails.
*Where:* `tests/test_docs_traces.py`, `tools/make_traces.py --check`.

**element read** -- one examination of an element of the input: `s[i]` costs 1,
`s[i:j]` costs `j - i`, iteration costs 1 per element, `len()` is free. The unit
of this repository's complexity lab, split into *positions* (search) and *slices*
(answer building).
*Where:* [`docs/05`](05-complexity-lab.md), `algorithms/support.py`.

**fuzzing** -- testing on many random inputs, usually with several input *shapes*
rather than one. Section "Three shapes, not one" in `docs/05` is the same idea
applied to benchmarking.
*Where:* [`docs/05`](05-complexity-lab.md), `tests/test_balanced_implementations.py`.

**hashable** -- usable as a dictionary key (`hash()` works and equality is
consistent with it). `index_cache` requires hashable values, so `[[1], [2]]`
raises `TypeError` there while `boyer_moore` handles it fine. Preconditions are
part of a contract, not an inconvenience.
*Where:* [`docs/02`](02-dominator.md), `tests/test_dominator_implementations.py`.

**invariant** -- a statement that is true at a known point in the code on every
iteration or every call, used to prove an algorithm correct. The Boyer-Moore
invariant is "after cancelling pairs, `count` copies of `candidate` remain"; the
balanced scan's is "`freq` holds exactly the counts of `s[start..end]`".
*Where:* [`docs/01`](01-balanced-strings.md), [`docs/02`](02-dominator.md).

**latent bug** -- a defect that currently cannot fire because something else
guards it. `legacy_equal_pair` answers `True` for a window containing *three*
letters when the first two counts match; it never matters because an independent
`distinct` counter short-circuits first. Delete one guard and the other is
silently wrong.
*Where:* [`docs/04`](04-bug-hunt.md) (B1b), `algorithms/balanced/core.py`.

**majority element** -- see *dominator*. "Strict" means `> n/2`; `= n/2` is not a
dominator, which is why `[1, 1, 2, 2]` has none.
*Where:* [`docs/02`](02-dominator.md).

**model (of a bug)** -- a small independent implementation of the behaviour you
*suspect* the code has, compared against the real thing over many inputs. If the
model matches, the diagnosis is proven; if it does not, your diagnosis is wrong
and you have saved yourself a half-fix.
*Where:* [`docs/04`](04-bug-hunt.md), `tests/test_original_characterization.py`.

**monotone / non-monotone** -- "growing the window never loses the property" /
"it can". Balance is non-monotone (`"ab"` is balanced, `"aba"` is not, `"abab"`
is), which is exactly why the two-pointer sliding-window trick does not apply,
and why every algorithm here enumerates windows or pairs instead.
*Where:* [`docs/01`](01-balanced-strings.md).

**oracle** -- an implementation that is obviously correct and too slow, used as
the standard against which fast implementations are tested. Here:
`algorithms/balanced/reference.py` (`O(n^3)`) and the direct definition
`is_balanced`. An oracle with an optimisation in it is a hypothesis the whole
test suite depends on.
*Where:* [`docs/01`](01-balanced-strings.md), [`docs/04`](04-bug-hunt.md).

**point read / slice read** -- the two halves of the element-read metric:
`point_reads` count single-element examinations (search work), `slice_reads` count
characters copied by slicing (answer building). Splitting them is what exposed the
`Theta(n^3)` copying bill inside an `O(n^2)` scan.
*Where:* [`docs/05`](05-complexity-lab.md).

**prefix sum** -- the running total of a sequence, usually stored as
`pre[k] = sum of the first k`. The pair scan converts "equal counts of two
letters" into `pre[i] == pre[j]`, which is a dictionary lookup instead of a scan.
*Where:* [`docs/01`](01-balanced-strings.md), `algorithms/balanced/fast.py`.

**precondition** -- a condition the caller must satisfy, which the function may
not check. `sort_and_pick_middle` needs comparable values; `index_cache` needs
hashable ones; `pair_scan` needs ASCII letters (and raises `ValueError` otherwise).
Documented, and tested: `tests/test_dominator_implementations.py` pins down what
happens when a precondition is violated.
*Where:* [`docs/02`](02-dominator.md).

**recursion limit** -- CPython's `sys.getrecursionlimit()`, 1000 by default, plus
the OS stack underneath it. This repository's recursions use one frame per
character of the scanned window, so their wall is 996 characters (measured;
997 raises), and `sys.setrecursionlimit` alone is a segfault trap -- raise the
thread stack too, as `algorithms.support.run_deep` does.
*Where:* [`docs/03`](03-recursion-vs-iteration.md), [`docs/04`](04-bug-hunt.md) (B4).

**sentinel** -- a special value used to mean "nothing here". Safe only if it
cannot also be real data: `None` as "no dominator" breaks on `[None, None, 1]`,
and `-1` as "no dominator" breaks nothing but tells the caller nothing. Preferred
in this repository: a distinct result type (`Dominator | None`) or a private
`object()` compared with `is`.
*Where:* [`docs/02`](02-dominator.md), [`docs/04`](04-bug-hunt.md) (B8, B12).

**silent wrong answer** -- a wrong result returned with no error, no warning and
no printed message. The worst severity class in this repository's taxonomy: the
loop submission answers `(0, [])` for `"aabbb"` and says nothing.
*Where:* [`docs/04`](04-bug-hunt.md), `tools/demo.py --scoreboard`.

**stack frame** -- one level of a Python call: its arguments, locals and return
address. Roughly 300 bytes here, and *per level* it is part of your capacity, not
an implementation detail: wrapping each recursive call in a logging function
halves the usable input (996 characters to ~497).
*Where:* [`docs/03`](03-recursion-vs-iteration.md).

**strictly more than half** -- the inequality in the definition of a dominator:
`count > n // 2`. Note `n // 2` integer division: for odd `n` this is the same as
`> n/2`, and for even `n` it excludes exactly-tied values.
*Where:* [`docs/02`](02-dominator.md).

**substring vs subsequence** -- a substring is contiguous (`"bb"` in `"aabbb"`); a
subsequence need not be (`"ab"` in `"ba"` is not a substring but is a
subsequence). Every problem in this repository is about substrings.
*Where:* [`docs/01`](01-balanced-strings.md).

**tail recursion** -- a recursive call that is the *last* thing a function does,
with no work left after it returns. `TryStart` is tail recursion, and tail
recursion is a loop: this repository rewrites it as one and measures that it costs
nothing.
*Where:* [`docs/03`](03-recursion-vs-iteration.md).

**tie** -- two different substrings attaining the same maximal length (`"abcabc"`
has three answers of length 2). Ties are the reason the contract returns a *list*,
and the reason the first oracle was wrong: it only replaced the answer when a
window was strictly longer, and silently dropped every tie.
*Where:* [`docs/01`](01-balanced-strings.md), [`docs/04`](04-bug-hunt.md).

**undo (backtracking)** -- mutate shared state before recursing and restore it
after, instead of copying it per level. `recursive_shared_freq` is the same search
as `recursive` with one frequency table instead of `n` copies; it is measurably
faster (101.5 ms against 138.7 ms on `"abab..."`, n = 500) and measurably easier
to get wrong -- the undo must happen on *every* exit path, including the early
one.
*Where:* [`docs/03`](03-recursion-vs-iteration.md).

**worst case (and why the quadratic scan survives it)** -- `brute_force` is
`O(n^2)` on paper but about `4n` on random 4-letter text, because a third letter
ends most scans immediately. The `O(n^2)` behaviour is real and reachable, and
`"abab..."` reaches it -- so the honest statement is "quadratic worst case,
near-linear on healthy input", which is also how one would describe the problem's
difficulty.
*Where:* [`docs/01`](01-balanced-strings.md), [`docs/05`](05-complexity-lab.md).

---

## Symbols

| symbol | meaning | example here |
|---|---|---|
| `n` | the size of the input | characters in the string, elements in the array |
| `k`, `L` | a length or count that is not the input size | window length, number of occurrences of a letter |
| `sigma` | the alphabet size | 26 here; `docs/05` measures what happens when it matters |
| `O(f)` | asymptotically bounded above (worst case, unless stated) | `brute_force` is `O(n^2)` |
| `Theta(f)` | bounded above **and** below | the pair scan copies `Theta(n^2)` on `"abab..."` |
| `C(a, b)` | binomial coefficient, "choose" | `C(26, 2) = 325` letter pairs |
| `x` (in tables) | a growth ratio between rows | `x4.0` per doubling means quadratic |
