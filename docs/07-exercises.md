# 07 -- Exercises, answers, and where to go next

Every chapter ends with its own exercise list; those are canonical and they are
graded by the chapter you just read. This file is the other half: a warm-up with
answers, the index that tells you which chapter to open depending on how much
time you have, five fully worked solutions (with measurements), and the
directions this repository deliberately did not take.

A mark next to a problem means:

* **(check)** -- the answer is a command you can run;
* **(prove)** -- the answer is an argument, not a number;
* **(measure)** -- the answer is a table you have to produce yourself;
* **(ship)** -- this is implemented in `algorithms/`, and the exercise is to
  re-derive it or improve it.

## Warm-up, with answers

Run each of these in a Python shell at the repository root first; the answers
follow.

```console
$ python -m tools.demo --scoreboard
$ python -m tools.demo
```

1. Is `"aba"` balanced? And `"abab"`? And `"aabbc"`?
2. Is "longest balanced substring" the same as "longest substring with at most
   two distinct characters"?
3. What does the archived `LBS_all_longest("aabbb")` return, and what is right?
4. What does the archived `LBS("café")` do?
5. What does `len("a" * 997)` have to do with the recursion limit?
6. What is Boyer-Moore's candidate for `[1, 1, 2, 3]`, and is it a dominator?
7. What does the archived `dominator([])` return? What should it return?
8. What does `find_dominator_indices([None, None, 1])` return? Why is that wrong?
9. What does `equal_pair([2, 2, 1] + [0] * 23)` return, and why does the
   archived program never notice?
10. What does `pair_scan("abcabc")` return? What did the *first* oracle return?
11. On `"abab..."` at `n = 1,000`, how much faster is `pair_scan` than
    `brute_force`? And on `"abc...z"` repeated at `n = 104`?
12. Which single-word change to `algorithms/balanced/iterative.py` makes
    `brute_force` twice as fast on random text, and why?

**Answers.**

1. `"aba"` no (a:2, b:1), `"abab"` yes (a:2, b:2), `"aabbc"` no (three distinct
   characters). The definition is in [`docs/01`](01-balanced-strings.md) §1.
2. No. The usual sliding-window problem is a *monotone* one; balance is not
   (`"ab"` is balanced, `"aba"` is not, `"abab"` is). The counterexample table is
   in [`docs/01`](01-balanced-strings.md) §2.
3. `(0, [])`; the right answer is `(4, ['aabb'])`. Bug B1: the balance test sits
   outside the `end` loop, so only the last window of each scan is ever tested.
4. It raises `IndexError`. `'é'.isalpha()` is `True`, so the guard lets it
   through, and `ord('é') - 97 = 136` is outside the 26-slot table. Bug B3.
5. `balanced.recursive("a" * 997)` raises `RecursionError`; `"a" * 996` is the
   largest input that survives, because the depth is one frame per character of
   the scanned window. B4, and [`docs/03`](03-recursion-vs-iteration.md) §6.
6. The candidate is `1` (the vote survives the `2` and the `3`, ending with
   `count == 1`). It is **not** a dominator: `1` occurs twice, and `2 <= 4 // 2`.
   Verifying the candidate is mandatory, not optional.
7. `-1` (there are no elements, so the verification count `0` is never `> 0`).
   The repository returns `None`; the sibling archived function returns `[]` for
   the same situation, which is bug B8 -- one problem, three dialects.
8. `[]` -- "no dominator". Wrong: `[None, None, 1]` *has* one, the value `None`,
   occurring twice in three elements. The archived program uses `None` as its
   "no answer" marker, so a real `None` collides with it (B12).
9. `False`. The archived version of that loop only looks at the first two
   non-zero counts, so `[2, 2, 1]` reads as "two equal counts" -- it would answer
   `True` if a third count did not matter. It never matters because an
   independent `distinct` counter rejects the window first: two guards, one of
   which is silently wrong (B1b).
10. `(2, ['ab', 'bc', 'ca'])`. The first oracle returned `(2, ['ab'])`: it only
    replaced the answer when a window was *strictly* longer, so every tie was
    dropped. The story is in [`docs/04`](04-bug-hunt.md#the-oracle-that-wasnt).
11. 485x faster on `"abab..."` (0.63 ms against 304.9 ms). On the 26-letter
    alphabet it *loses* by about 20x (2,489 us against 127 us) -- the quadratic
    scan's `break` makes it linear on a wide alphabet, while the pair scan always
    visits all 325 pairs. Both tables: [`docs/05`](05-complexity-lab.md).
12. Replace the 26-slot balance test (`equal_pair`) with the two-integer test
    "`distinct == 2` and `2 * max_count == window length`". Same answers, same
    read counts, 2.1x faster on random text -- and 10% *slower* on `"aaaa..."`
    where the 26-slot test was never reached anyway. Shipped as
    `brute_force_incremental`; the proof is below.

## Which chapter to open, given the time you have

| time | do this | where |
|---|---|---|
| 10 minutes | the warm-up above, then `python -m tools.demo` | this file, [`docs/00`](00-start-here.md) |
| 30 minutes | reproduce B1 with your own three assertions, then fix it | [`docs/04`](04-bug-hunt.md), [`docs/01`](01-balanced-strings.md) §4 |
| 1 hour | translate `TryStart`/`TryEnd` into loops yourself; compare with `round_trip` | [`docs/03`](03-recursion-vs-iteration.md) |
| 2 hours | prove the pair scan, then break it on a 26-letter alphabet | [`docs/01`](01-balanced-strings.md) §7, [`docs/05`](05-complexity-lab.md) |
| an afternoon | the five worked solutions below, in order | this file |
| a weekend | one of the projects at the end | this file |

## Worked solution 1 -- the O(1) balance test **(ship)**

*Chapter exercise: [`docs/01`](01-balanced-strings.md) §11, exercise 3.*

The balance test walks all 26 slots for every window. Can it be `O(1)`?

Yes, with two integers that the scan already has or can maintain for free:

* `distinct` -- how many different letters the window uses (already maintained
  incrementally, and it is what terminates the scan);
* `max_count` -- the largest count in the table, which is one comparison to
  update when a letter is counted.

**Claim.** When `distinct == 2`, the two counts are equal *if and only if*
`2 * max_count == window length`.

*Proof.* Let the window have length `L` and two letters with counts `a`, `b`, so
`a + b = L`.
(⇒) If `a == b` then `a == L/2`, and the larger of the two is `L/2`.
(⇐) If the larger is `L/2`, the other is `L - L/2 == L/2`, so they are equal. ∎

Both directions matter: the claim is an equivalence, not a sufficient condition,
which is why the implementation needs no extra guard.

```python
if distinct == 2 and 2 * max_count == end - start + 1:
    tracker.consider_span(text, start, end)
```

**Measured** (`n = 1,000`, best of five; the same machine as
`docs/traces/bench.txt`):

| shape | `brute_force` | `brute_force_incremental` | ratio |
|---|---|---|---|
| random over `abcd` | 1.72 ms | **0.85 ms** | 2.0x faster |
| `"ababab..."` | 304.9 ms | **80.6 ms** | 3.8x faster |
| `"aaaa..."` | 46.8 ms | 51.8 ms | 10% slower |

Three lessons, in order of how much they surprise people:

1. **The same algorithm can be 4x faster.** The element-read counts are
   *identical* to `brute_force` (4,295 positions and 96 slices at `n = 1,000` on
   random text) -- the improvement is entirely inside the constant the
   complexity analysis throws away. A read counter cannot see it; only a timer
   can.
2. **The same algorithm can be 10% slower.** On `"aaaa..."` the window never
   reaches the balance test (`distinct` is 1), so the 26-slot walk being replaced
   was not being executed at all, and the extra `max_count` comparison per
   character is pure overhead. "Optimisation" is a statement about a shape.
3. **This is not the pair scan's replacement.** On `"abab..."` the incremental
   loop at `n = 1,000` takes 80.6 ms against the pair scan's 0.63 ms: 128x. A
   constant-factor win does not change a complexity class.

Correctness was checked the same way everything else here is: exhaustively
against the oracle on every string over `{a, b, c}` up to length 8, through the
shared registry, and by asserting that the two balance tests agree on every
reachable frequency table for 3,000 random windows.

## Worked solution 2 -- collect the answers in a second pass **(ship)**

*Chapter exercise: [`docs/01`](01-balanced-strings.md) §11, exercise 6.*

`pair_scan` slices whenever it sets a record. On `"abab..."` the records keep
improving, so it copies 500,000 characters at `n = 1,000` to return a single
answer of length 1,000. The fix is to separate **finding the length** from
**collecting the strings**:

1. pass one: prefix sums and a dictionary, no slicing at all -- keep only the
   best length;
2. pass two: walk the pairs again and slice only windows whose length equals that
   best length.

Measured on `"abab..."` (`docs/traces/bench.txt`):

| | positions (n = 800) | slices (n = 800) | time (n = 500) | time (n = 1,000) |
|---|---|---|---|---|
| `pair_scan` | 1,600 | 320,000 | 0.28 ms | 0.63 ms |
| `pair_scan_two_pass` | 2,400 | **800** | 0.24 ms | 0.47 ms |

400x fewer sliced characters, 25% less time, 50% more positions -- and on random
text the same change costs 90% more time (3.03 ms against 1.59 ms), because the
second walk collects almost nothing. Two comments worth keeping:

* the worst case of pass two is still `Theta(n^2)` copying, when the *answer
  itself* is that large (many windows of the maximum length);
* the trick is only available because the contract asks for the substrings. If it
  asked for the length, `pair_scan` would already be linear in copying -- an API
  decision that changes the complexity, which is worth remembering the next time
  someone asks for "just the strings too".

## Worked solution 3 -- is the divide & conquer's count ever needed?

*Chapter exercise: [`docs/02`](02-dominator.md) §8, exercise 3.*

The archived recursion, when both halves return the **same** candidate `x`,
still counts `x` over the whole range and gives up if the count is not a
majority. Can that count ever fail?

**Claim.** No -- provided every candidate a half returns is a *verified*
majority of that half, which is exactly what the archived code guarantees (its
base cases return only equal pairs, and every other return is guarded by
`count > size // 2`).

*Proof.* Let the two halves have sizes `p` and `q`, and let `x` be a strict
majority of both. Then `count_left >= floor(p/2) + 1` and
`count_right >= floor(q/2) + 1`, so

```
count(x) >= floor(p/2) + floor(q/2) + 2 > (p + q) / 2
```

so `x` is a strict majority of the union. ∎

**Measured** (exhaustive over all arrays of length ≤ 7 over three values, plus
4,000 random arrays up to length 40, instrumented copy of the archived logic):

| event | count |
|---|---|
| agree-branch entered (both halves returned the same `x`) | 4,253 |
| agree-branch count that failed | **0** |
| separate counts performed (halves disagreed) | 40,410 |

So the count in the agree branch is redundant *for correctness* -- but it is
**not dead code**, and the reason is bug B10: the archived function also returns
the *indices* of the dominator within the current range, and the count loop is
where those indices get rebuilt. In a candidate-only implementation (like
`algorithms/dominator/divide.py`) the agree branch is a single `return left`, the
counts fall by about 10%, and the indices are collected once at the top.

```python
if left is right and left is not _NOTHING:
    return left                      # certified by the claim above
```

Two habits this exercise is really about: "is this check reachable?" is a
question with a *measurement* for an answer, and "redundant" and "dead" are
different verdicts.

## Worked solution 4 -- find the recursion wall **(measure)**

*Chapter exercise: [`docs/03`](03-recursion-vs-iteration.md) §8, exercise 7.*

"Find the largest `n` for which `recursive("a" * n)` succeeds." It depends on how
many frames are already on the stack when the call starts, and the differences
are exactly the frames you added:

| called from | largest `n` that survives |
|---|---|
| module level of a script | **996** |
| inside one helper function | 995 |
| inside a `unittest` method (the test runner is ~15 frames deep) | 981 |
| through a wrapper that logs entry and exit per call | ~495 |

So `tests/test_recursion.py` does not assert 996 anywhere: it asserts *shapes*
(`recursive_depth("ab" * 10) == 21`), and it stays well clear of the boundary
("`"a" * 900` works, `"a" * 1100` raises"). A test that pins the exact wall would
fail the day somebody adds a decorator.

The number to remember is not 996; it is `stack_frames_per_character x n`, and
CPython's default budget is 1,000 frames *plus* whatever the OS stack can take.
`sys.setrecursionlimit(20000)` on its own is a trap: the C stack runs out first
and the process dies with a segmentation fault instead of an exception. Raising
the thread stack too is what `algorithms.support.run_deep` does.

## Worked solution 5 -- when does the pair scan lose?

*Chapter exercise: [`docs/05`](05-complexity-lab.md) §Exercises, exercise 3.*

The quadratic scan's `break` fires as soon as a third letter appears. On a wide
alphabet that happens immediately, so `brute_force` is really `O(n)` with a tiny
constant, while `pair_scan` still pays for all 325 pairs:

| n (alphabet 26, repeated) | `brute_force` | positions | `pair_scan` | positions |
|---|---|---|---|---|
| 26 | 31.7 us | 75 | 1,192 us | 676 |
| 104 | 126.8 us | 309 | 2,489 us | 2,704 |
| 260 | 314.5 us | 777 | 5,178 us | 6,760 |

Both are linear in `n` here; the constants are `~3n` against `~26n`, and the
"dumb" algorithm wins by 20x. The pair scan's guarantee is about *two-letter*
adversarial input; on healthy text with a wide alphabet it is paying insurance it
does not need.

**Generalising:** the pair scan's work is `(sigma - 1) * n` per pass, where
`sigma` is the number of *distinct letters that actually occur*. So the crossover
against the quadratic scan's `~3n` on healthy input sits at `sigma ≈ 4` -- which
is precisely the shape the benchmark calls "random, 4 letters", and precisely why
the two implementations are within 8% there and 485x apart two shapes over. A
benchmark with one column would have picked whichever answer the alphabet size
happened to give.

## Where to go next

### the generalisation the pair scan is a special case of

The pair scan encodes "these two letters occur equally often" as an equality of
two prefix sums. For *exactly `k` distinct letters, each equally often*, the same
construction uses a key of `k - 1` count differences:

* `k = 2`: one integer (the pair scan in `algorithms/balanced/fast.py`);
* `k = 3`: two integers -- keep a dictionary from `(count[a] - count[b],
  count[b] - count[c])` to its first occurrence (this is the technique in the
  editorial for LeetCode 3714, *Longest Balanced Substring II*, which also shows
  why resetting the map at every "other letter" is required);
* general `k`: `k - 1` integers, one linear pass **per subset of letters**, i.e.
  `C(26, k) * n` work -- 325 passes for pairs, 2,600 for triples, 230,230 for
  quadruples.

So "the problem is linear" is true *per subset*, and the whole difficulty of the
general problem is that there are exponentially many subsets. This is the honest
version of the claim in [`docs/01`](01-balanced-strings.md) §7.

### the general-alphabet problem (what this repository does not settle)

The pair scan is a union of 325 two-letter problems, and §7 of
[`docs/01`](01-balanced-strings.md) is honest about the bill: `C(26, 2) * n`
passes, growing as `C(26, k)` if you want `k` distinct characters at once.

What is *not* in this repository is an algorithm that handles all 26 letters
jointly. The linear-time constructions we could find cover two or three distinct
characters, where hashing prefix count differences gives a single pass (search
*longest well-balanced substring*, or LeetCode 3713/3714); neither lifts to the
full alphabet in a paragraph, and neither has the property this repository cares
about, which is that a reader can check it against an oracle in an afternoon. If
you do find or derive one, keep `reference` as its oracle: a fast algorithm with
an oracle is a result, a fast algorithm without one is a rumour.

### two more directions with the same shape

* **Dominators beyond `n/2`.** "At most `k - 1` values can occur more than `n/k`
  times" is the generalisation that a Misra-Gries summary solves in one pass with
  `O(k)` counters; the Boyer-Moore vote is the `k = 2` case. Exercise:
  reimplement `algorithms/dominator/vote.py` for `k` counters and verify against
  `index_cache` on random arrays.
* **Streaming dominators.** Boyer-Moore is the only implementation here that
  works in one pass with `O(1)` memory, and it still needs a *second* pass to
  verify. Find the input shape that makes the verification unavoidable and state
  the information-theoretic excuse (`docs/02` exercise 5).

## Projects

1. **`k`-balanced, properly.** Add `exactly_k_balanced` for `k = 3` using the
   two-difference key, exhaustively test it against a generalised oracle
   (`is_balanced_k`), and add a benchmark row. Expect it to lose to the pair scan
   on two-letter input and win everywhere the alphabet is wide.
2. **Mutation testing.** Write a harness that mutates the eight balanced
   implementations and the four dominator implementations (swap `<` for `<=`,
   delete `equal_pair`, flip a `break`), runs the test suite, and reports which
   mutants survive. Surviving mutants are the test suite's *actual* blind spots
   -- and the numbers make a good chapter of their own.
3. **A trace viewer.** `algorithms/tracing.py` produces ASCII. Emit JSON events
   from the same hook (`trace=`) and render them in the playground, so the
   architecture of a call tree becomes something you can scrub through rather
   than something you read.
4. **Package it.** Give `algorithms/` a `pyproject.toml`, CI across Python
   3.8-3.13 (the recursion wall changes with the version -- measure it), a
   `ruff`/`mypy` pass, and a `pytest` runner that keeps the `unittest` suite as
   the source of truth. The interesting part is discovering which claims in the
   documentation are version-dependent.
5. **One more review.** Take another student submission for either problem --
   from a classmate, from a public repository, from your own past self -- and run
   it through the same pipeline: oracle, exhaustive differential test,
   characterization tests, read counts. The catalogue in
   [`docs/04`](04-bug-hunt.md) is a template; the value is in the second
   application of it.
6. **Explain it to somebody.** The strongest test of this repository is whether
   you can explain, to a peer who has read none of it, why
   `LBS_all_longest("aabbb")` returns `(0, [])` and what the one-line fix is.
   If you need this repository in front of you, one of the two chapters is still
   too clever for its own good -- and that is a bug report worth writing.
