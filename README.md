# Balanced substrings & Dominators

### Four student programs, taken seriously: read, traced, proven, and made fast

This repository is a small, self-contained study of two classic exercises,
each solved twice -- once with loops, once with recursion:

|  | non-recursive | recursive |
|---|---|---|
| **balanced substrings** | double loop over `start`/`end` | `TryStart` / `TryEnd` |
| **dominators** (majority element) | Boyer-Moore vote | divide & conquer |

The four submitted programs are archived **byte for byte**, bugs and all. Around
them this repository adds: a corrected implementation of each algorithm, a fast
algorithm that neither submission attempted, tests that prove every claim, ASCII
traces of what the code actually does, benchmarks with real numbers, and eight
chapters of explanation.

It is written for somebody who wants to *understand* these two problems rather
than copy an answer: every statement in `docs/` is backed by a runnable check.

```console
$ python -m tools.demo                 # a five-minute guided tour
$ python -m unittest discover -s tests -t .   # 190 tests, ~12 s, no dependencies
$ python -m tools.run_all              # tour + tests + trace freshness check
```

No third-party packages. Python 3.8+ (developed on 3.11).

---

## The verdict, in one table

Two programs, one problem, three different answers:

| input | correct answer | submitted loop | submitted recursion |
|---|---|---|---|
| `'aabbb'` | `4 ['aabb']` | **`0 []`** | `4 ['aabb']` |
| `'aabbc'` | `4 ['aabb']` | **`2 ['bc']`** | `4 ['aabb']` |
| `'abcabc'` | `2 ['ab', 'bc', 'ca']` | **`2 ['bc']`** | `2 ['ab', 'bc', 'ca']` |
| `'aabbaa'` | `4 ['aabb', 'abba', 'bbaa']` | **`4 ['bbaa']`** | `4 ['aabb', 'abba', 'bbaa']` |
| `'ababab'` | `6 ['ababab']` | `6 ['ababab']` | `6 ['ababab']` |

(the whole table, plus dominators, is in `docs/traces/balanced-bug-table.txt`)

**The headline finding.** The non-recursive program moves its balance test
*outside* the inner loop, so for each starting position it only ever examines the
last window its scan touched. Everything else is thrown away. It is not a
performance bug: on `'aabbb'` it silently reports *"there is no balanced
substring"* about a string that contains `'aabb'`. The repository does not just
claim this, it proves it: `tests/test_original_characterization.py` models the
misplaced check in ten lines and shows the submission matches that model on
20,000 random inputs and on every string up to length 7 over `{a, b, c}`.

**The recursive program is right.** That is the other half of the finding, and
it is the more useful one for a reader: it deals with non-letter input by
stopping the scan instead of crashing, it gets every example right, and its
bugs are of a completely different kind -- a non-ASCII letter crashes it, a
996-character string exhausts the stack, and it never tells you that it
quietly decided to stop scanning.

---

## What is here

```
algorithms/
  original/                 the four submissions, frozen (digests in FROZEN.sha256)
    adapters.py             wrap their odd return shapes in a modern contract
    FROZEN.sha256           proof that the archive was not "tidied up"
  balanced/                 balanced substrings: the problem, eight ways
    core.py                 what "balanced" means, input policy, BestTracker
    reference.py            the obvious O(n^3) oracle
    iterative.py            the repaired double loop, and the recursion unrolled
    recursion.py            the repaired TryStart/TryEnd recursion
    fast.py                 the pair scan: 325 letter pairs + prefix sums
  dominator/                dominators: four strategies + one result type
  tracing.py                call trees, vote walks and scan tables as ASCII
  support.py                ReadCounter (element reads), deep recursion, timing
docs/                       the course: 8 chapters + docs/traces/*.txt (real output)
tests/                      190 tests; every claim in the docs has one
tools/                      demo, bench, traces, freeze, run_all, playground server
playground/index.html       click through the algorithms in a browser
```

## Where to start

| you want to... | read |
|---|---|
| see it work in five minutes | `python -m tools.demo` |
| understand the balanced-substring problem | [`docs/01-balanced-strings.md`](docs/01-balanced-strings.md) |
| understand dominators and their proofs | [`docs/02-dominator.md`](docs/02-dominator.md) |
| see recursion and loops as the same thing | [`docs/03-recursion-vs-iteration.md`](docs/03-recursion-vs-iteration.md) |
| see every bug, with a reproduction | [`docs/04-bug-hunt.md`](docs/04-bug-hunt.md) |
| see how the numbers were measured | [`docs/05-complexity-lab.md`](docs/05-complexity-lab.md) |
| click instead of read | `playground/index.html` |
| get the map of everything | [`docs/00-start-here.md`](docs/00-start-here.md) |

## The two problems, stated properly

**Balanced substring.** A string is *balanced* when it uses **exactly two
distinct characters** and each occurs **the same number of times**. Given a
string, find the longest balanced substring and list every distinct substring of
that length. `'ab'`, `'aabb'` and `'abba'` are balanced; `'aaaa'` is not (one
character), `'aabbb'` is not (counts differ), `'aabbc'` is not (three
characters).

The trap: this is *not* the usual "longest substring with at most two distinct
characters". Balance is not a monotone property of window length, so the sliding
window that solves the usual version does not apply here. `'aabb'` is balanced,
`'aabbc'` is not, `'aabbc'` cut back to `'aabb'` is balanced again -- no
monotonicity to exploit. See [`docs/01`](docs/01-balanced-strings.md) for the
counterexample that kills the greedy.

**Dominator.** An element is a *dominator* (majority element) of a sequence when
it occurs **strictly more than half** the time. At most one value can dominate,
so the question is always "which one, if any". Four implementations here:
Boyer-Moore's vote plus verification, a divide & conquer based on the halving
lemma, a dictionary of indices, and "sort and look at the middle".

## Ten things this repository will convince you of

1. **Correctness has to be checked against an oracle, not against intuition.**
   The O(n^3) `reference` implementation exists for exactly one reason.
2. **A silent wrong answer is worse than a crash.** The loop submission returns
   `(0, [])` for input with a four-character answer; the recursion returns
   correct answers and *crashes* on `'café'`. One of those is easy to notice.
3. **A bug can hide behind the examples that happen to work.** `'aabb'` and
   `'abab'` are answered correctly, which is why the bug survived.
4. **If a claim can be modelled, model it.** "The test is outside the loop" is
   a hypothesis until a ten-line model reproduces the submission on 20,000
   inputs.
5. **`None`, `-1` and `[]` are not interchangeable sentinels.** Using a real
   value as your "nothing" marker makes a whole class of inputs unanswerable.
6. **Recursion depth is a resource with a hard limit**, and in CPython it is one
   frame per level, no tail-call optimisation, ~1000 by default.
7. **Copy-on-recurse vs mutate-and-undo** is a real measured difference, not a
   style preference (and both are correct -- that is the interesting part).
8. **The obvious slow solution is the one you can be sure about**, and being
   sure is what makes the fast one trustworthy.
9. **`O(n)` search can still pay an `O(n^2)` copying bill.** Separate the
   metrics or you will mislead yourself; `docs/05` shows both.
10. **A faster algorithm is not always faster.** On random 4-letter input the
    sophisticated pair scan beats the quadratic scan by less than 2x; on
    `'ababab...'` it beats it by 485x. Complexity classes describe a *trend*,
    and constants decide the region you are actually in.

## How the guaranteed-to-be-true part works

Nothing in this repository is asserted in prose without a test that would fail
if it were false:

* **Differential tests.** All eight balanced-string implementations are compared
  against the oracle on *every* string up to length 10 over two letters, length 8
  over three letters, and length 6 over four letters, plus randomised longer
  inputs (`tests/test_balanced_implementations.py`).
* **Characterization tests.** The archived programs are pinned to their observed
  behaviour, including the bugs, so nobody can "fix history" by accident
  (`tests/test_original_characterization.py`, plus SHA-256 digests in
  `algorithms/original/FROZEN.sha256`).
* **Static analysis.** The claim that a variable in the submission is dead code
  is checked with the `ast` module, not by eyeballing it.
* **Measurement.** Element reads are counted in the code
  (`algorithms/support.ReadCounter`), so complexity claims come with numbers
  rather than adjectives.
* **Documentation freshness.** Every trace quoted in `docs/` is generated by
  `tools/make_traces.py` and compared with the file on disk by
  `tests/test_docs_traces.py`. Stale documentation fails the build.
* **The oracle itself was wrong once** (an "obvious" speed-up that dropped
  ties). The story is in [`docs/04`](docs/04-bug-hunt.md) -- it is the best
  argument in the repository for writing the slow, obvious version first.

## Playground

`playground/index.html` is a single self-contained page (no build step, no
dependencies): step through the repaired scan window by window, watch
Boyer-Moore cancel votes, see the archived loop give a wrong answer next to the
right one, and measure the recursion depth budget. Open it directly, or serve it:

```console
$ python -m tools.serve_playground                # http://localhost:8000
```

`tools/serve_playground.py` is thirty lines of stdlib around
`http.server` that fix the four habits which show up when a page is loaded
through a proxy or an iframe: it speaks HTTP/1.1 (so the connection stays warm),
raises the listen backlog from 5 to 128, declares `charset=utf-8` on every
content type, and sends `Cache-Control: no-store` so a cached copy can never
shadow a regenerated page. The plain fallback still works if you prefer no
repository code in the serving path:

```console
$ python -m http.server 8000 --directory playground
```

The page re-implements the algorithms in JavaScript, which makes it a second
place for bugs to live, so it is checked like everything else: `python -m
tools.check_playground` compares its functions with the Python ones on 75
strings and 54 arrays (``None``/``null`` included), audits the page's wiring, and
re-runs the exhaustive `{a, b, c}` sweep inside the page's own code. It needs
`node`, and skips politely without it.

## Status and caveats

* **The archive is frozen on purpose.** Do not edit `algorithms/original/*.py`;
  revert the edit instead, or re-create the archive deliberately with
  `python -m tools.freeze_archive`.
* **The pair scan is not asymptotically optimal.** It spends `C(26, 2) = 325`
  linear passes, one per pair of letters -- honest, checkable, and enough to beat
  the quadratic scans by two to three orders of magnitude on adversarial input.
  The linear-time constructions we could find handle two or three distinct
  letters (hashing prefix count differences, as in LeetCode 3714); they do not
  extend to the unrestricted alphabet in a paragraph, so `docs/01` §7 and
  `docs/07` state what this repository does and does not claim.
* **Timings are machine-specific.** `docs/traces/bench.txt` records the run
  behind `docs/05`; the shapes of those tables are the part that generalises.
* **No license has been chosen yet.** Add one before sharing this widely.
