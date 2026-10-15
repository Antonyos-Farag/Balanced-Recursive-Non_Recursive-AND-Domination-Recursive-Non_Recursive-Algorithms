# 05 -- The complexity lab

Big-O tells you how cost *trends*; it says nothing about the region you are
actually working in, and it hides constant factors that can be three orders of
magnitude wide. This chapter is the practical complement: for every algorithm in
this repository, count the work it does, then time it, and keep the two numbers
apart because they answer different questions.

Everything here is reproducible in one command:

```console
$ python -m tools.make_traces      # rewrites docs/traces/, including bench.txt
$ python -m tools.bench --sizes 125,250,500,1000 --repeat 3
$ python -m unittest tests.test_support tests.test_docs_traces -v
```

## How these numbers were made

`algorithms/support.py` provides a sequence proxy that counts how often the code
under test looks at an element:

```python
>>> from algorithms.support import ReadCounter
>>> from algorithms.balanced import brute_force_normalized
>>> counter = ReadCounter("abab")
>>> brute_force_normalized(counter)
(4, ['abab'])
>>> counter.point_reads, counter.slice_reads, counter.reads
(10, 6, 16)
```

* **`point_reads`** -- single-element accesses (`text[i]`) and iterated elements.
  This is **search work**: the algorithm had to examine an element.
* **`slice_reads`** -- characters copied by slicing (`text[i:j]` counts `j - i`).
  This is **answer building**: work spent materialising a result.
* `reads` is the sum, for convenience.

Why count at all? Because counts do not depend on the machine, the Python build,
or what else is running. A quadratic algorithm shows itself as "four times the
reads when `n` doubles", every time, on every laptop. Timings reproduce the
*shape* of a table; the counts reproduce the *table*.

Three deliberate choices:

1. **Reads are counted in a separate, single run.** The first version of
   `tools/bench.py` timed the instrumented call, so `repeat=3` tripled the read
   counts -- caught by reading the table, where `index_cache` (one pass over `n`
   elements) cheerfully reported `3n`. Measure with the counter, time without it.
2. **Timings are best-of-three** (`support.timed(..., repeat=3)`), not the mean:
   the mean is dominated by whatever else the machine was doing, while the
   fastest run is the least noisy estimate of what the code itself costs.
3. **Nothing is hidden.** Every table quoted below exists as raw output in
   `docs/traces/bench.txt`, with the command that produced it at the top.

What the counting **excludes**: `len()` is free (the algorithm does not examine
an element); the 26-slot frequency scan inside `equal_pair` is not counted (it
reads a list of *counts*, not the input); and two accesses to the same character
count twice, so `round_trip` -- which reads `text[end]` once for `isalpha()` and
once for `ord()` -- reports double the point reads of `brute_force` for the same
work. The metric answers "how much of the input did you touch?", not "how much
work did you do?". Time answers that one, at least for the Python-level part.

## Three shapes, not one

A single benchmark on "random input" would have flattered the quadratic scan into
looking competitive and hidden the entire story. Every table is produced on three
shapes:

| shape | what it is | who it favours |
|---|---|---|
| random, 4 letters | random over `abcd` | the quadratic scans (most windows die at the third letter) |
| `"ababab..."` | two letters, alternating, never a third | the pair scan (the quadratic scan has no shortcut left) |
| `"aaaa..."` | one letter, repeated | the pair scan (the quadratic scan does full work and finds nothing) |

Producing all three is a rule worth adopting: **benchmark the shape you hope for,
the shape you fear, and the degenerate shape.** A table with one column of
numbers is not evidence.

## The scaling table

From `docs/traces/balanced-scaling.txt` (element reads on `"ababab..."`; the file
prints the growth ratio between consecutive doublings of `n`):

| implementation | n = 100 | n = 200 | n = 400 | n = 800 | growth per doubling |
|---|---|---|---|---|---|
| `reference` (positions) | 0 | 0 | 0 | 0 | -- |
| `reference` (slices) | 171,700 | -- | -- | -- | **x7.6-7.8** |
| `brute_force` (positions) | 5,050 | 20,100 | 80,200 | 320,400 | **x4.0** |
| `brute_force` (slices) | 2,550 | 10,100 | 40,200 | 160,400 | x4.0 |
| `pair_scan` (positions) | 200 | 400 | 800 | 1,600 | **x2.0** |
| `pair_scan` (slices) | 5,000 | 20,000 | 80,000 | 320,000 | **x4.0** |
| `pair_scan_two_pass` (positions) | 300 | 600 | 1,200 | 2,400 | x2.0 |
| `pair_scan_two_pass` (slices) | 100 | 200 | 400 | 800 | **x2.0** |

Read the ratios, not the absolute numbers -- the ratio is the complexity class:

* `reference` is `O(n^3)`, and a doubling of `n` costs `x8`. It stops at `n = 100`
  because watching `n^3` grow is an exercise nobody needs twice.
* `brute_force` is `O(n^2)` in both columns: `x4.0` per doubling, exactly.
* `pair_scan` **examines** a number of characters proportional to `n` (x2.0) while
  **copying** a number proportional to `n^2` (x4.0). One algorithm, two bills, two
  complexity classes.

That last row is why the counter is split in two. A single "element reads" column
would have reported `pair_scan` as quadratic and been formally right and
practically misleading: on this input it is 480x faster than the quadratic scan
(see the next section), because the `x4.0` is paid in `memcpy` (C, per character
of a slice) while `brute_force`'s `x4.0` is paid in Python loop iterations (one
interpreter step per character examined).

`pair_scan_two_pass` is the same search with the copying bill paid once at the
end instead of continuously; it costs 1.5x the positions and turns the slice
column into `x2.0`. The trade-off is measured in "The copying bill" below.

## The measurement that changed the code

The first version of the quadratic scan did the natural thing:

```python
if distinct == 2 and equal_pair(freq):
    tracker.consider(text[start:end + 1])      # build the substring, then decide
```

The substring is built *before* the tracker is asked whether it is interesting.
On `"ababab..."` there are `Theta(n^2)` balanced windows, and building each one
costs `Theta(L)` for a window of length `L`, so the program was **cubic** even
though the scan was quadratic.

It was invisible. The timing table looked fine -- slicing is a `memcpy`, and the
quadratic scan was already hopeless on that shape for other reasons. What made it
visible was counting the *copies* separately from the *examinations*:

| `brute_force` on `"ab" * 250` (n = 500) | element reads |
|---|---|
| building every balanced window before testing it | 10,604,500 |
| asking first, building only what can win | **188,000** |

The fix lives in `BestTracker.consider_span`, and it is four lines:

```python
def consider_span(self, text, start, end):
    """Offer text[start:end+1] without building it unless it can win."""
    size = end - start + 1
    if size < self.length or size < 1:
        return
    self.consider(text[start : end + 1])
```

Nothing about the algorithm changed -- same windows, same answers, same
complexity class for the search. Only the *decision of when to build the answer*
moved, and the copies fell by a factor of 56. The 188,000 that remain are exactly
the two bills that cannot be avoided: 125,250 positions (the scan's `n^2 / 2`)
plus 62,750 characters of answer material (every time a new record is set, its
substring is copied).

Two lessons, and the second is the one people skip:

1. **Measure the thing you actually compute**, including the parts that feel
   free: constructing results, formatting strings, copying lists, joining a
   string in a loop.
2. **A metric that hides a 56x difference is a broken metric.** When the timer
   says "fine" and the counter says "cubic", neither is wrong -- the *metric* is
   incomplete, and the honest response is to split it, not to pick a favourite.

## Wall-clock time, all three shapes

From `docs/traces/bench.txt`, `n = 1000` (the recursions are absent by 1000: one
frame per character of window, and the limit is 996 -- see
[`docs/03`](03-recursion-vs-iteration.md)):

| shape | `brute_force` | `brute_force_incremental` | `pair_scan` | `pair_scan_two_pass` | speed-up |
|---|---|---|---|---|---|
| random, 4 letters | 1.72 ms | **0.85 ms** | 1.59 ms | 3.03 ms | 1.08x |
| `"ababab..."` | 304.9 ms | 80.6 ms | 0.63 ms | 0.47 ms | 485x |
| `"aaaa..."` | 46.8 ms | 51.8 ms | 0.053 ms | 0.054 ms | 880x |

Five things to notice:

1. **On random input the fanciest algorithm loses to a `for` loop with a better
   constant.** `brute_force_incremental` -- the same double loop, with the
   26-slot balance test replaced by two integers -- is the fastest implementation
   in the package on random 4-letter text (0.85 ms against the pair scan's
   1.59 ms), and it is 3.8x faster than its own starting point on `"abab..."`.
   Its **read counts are identical** to `brute_force`'s on every shape (4,295
   positions and 96 slices at `n = 1,000` on random text; 500,500 and 250,500 on
   `"abab..."`). The counter cannot see this difference *at all*; only the timer
   can. That is the single best argument in this chapter for keeping both
   instruments.
2. **On random input the fancy algorithm is barely ahead.** Almost every window
   dies at the third letter, so `brute_force` does about `4n` examinations instead
   of `n^2 / 2`, and the pair scan's fixed overhead (325 pairs, each with its own
   walk and sort) cancels the advantage. If you benchmark only random text you
   will conclude that the whole exercise was pointless. You will be wrong, and
   the next row is why.
3. **Adversarial input is where complexity classes bite**: 485x on two letters.
   The crossover on `"abab..."` is *below* the smallest size tested -- the pair
   scan is already faster at `n = 10` (12.8 us against 31.9 us, best of five),
   because 325 short walks beat 55 Python-level window iterations.
4. **A single letter is the quadratic scan's nightmare**: 880x on a string whose
   answer is "nothing, length 0". Nothing ever dies (so no early `break`) and
   nothing is ever balanced (so no record is set), which is exactly the case the
   quadratic scan has no shortcut for.
5. **The two-pass variant wins on the adversarial shapes and loses on random
   text.** On `"abab..."` it is the fastest implementation in the package; on
   random text it is twice as slow as the single-pass version it improves,
   because it walks every pair twice and the second walk finds few answers to
   collect. Fastest is not a property of a function; it is a property of a
   function *on a shape*.

And a sixth, which is the most uncomfortable one for this chapter's narrative:

6. **The pair scan can lose badly on a *wide* alphabet.** Measure the two on
   `"abc...z"` repeated -- every letter present, no pair dominating:

   | n | `brute_force` | reads | `pair_scan` | reads |
   |---|---|---|---|---|
   | 26 | 31.7 us | 75 | 1,192 us | 676 |
   | 104 | 126.8 us | 309 | 2,489 us | 2,704 |
   | 260 | 314.5 us | 777 | 5,178 us | 6,760 |

   The quadratic scan examines **three characters per start** on this shape: the
   third distinct letter arrives immediately and its `break` fires, so its
   `O(n^2)` worst case never happens and it is really `O(n)` with a tiny
   constant. The pair scan, meanwhile, pays for all 325 pairs whether they occur
   or not -- 26 positions per character here. On a wide alphabet, the "dumb"
   algorithm is 20x faster than the "smart" one *and* asymptotically fine.

   This is the honest boundary of the story: the pair scan buys a guarantee about
   adversarial *two-letter* input, and pays for it on healthy multi-letter input.
   Knowing which regime your data is in is part of choosing the algorithm --
   which is exactly why the tables have three shapes in them and not one.

The recursions, at `n = 500` (`"abab..."`), for completeness:

| implementation | positions | slices | time |
|---|---|---|---|
| `brute_force` | 125,250 | 62,750 | 77.2 ms |
| `recursive` (copy `freq[:]` per level) | 125,250 | 62,750 | 138.7 ms |
| `recursive_shared_freq` (mutate and undo) | 125,250 | 62,750 | 101.5 ms |
| `pair_scan` | 1,000 | 125,000 | 0.28 ms |

Identical read counts, different times: the difference is what the machine does
*between* the reads. Copying a 26-slot list per call costs 1.8x against the
loop's `freq` reuse, and un-doing the mutation (the backtracking version) buys
back 36% of that. None of it shows up in a read counter -- which is why you need
both instruments. [`docs/03`](03-recursion-vs-iteration.md) is the chapter about
that difference.

## The copying bill, and the variant that pays it once

`pair_scan` collects answers as it walks: every time a prefix sum repeats to form
a record-breaking window, it slices. On `"abab..."` the records keep improving
for `Theta(n)` steps and the slices get longer as they go -- `Theta(n^2)`
characters copied, 500,000 of them at `n = 1,000`, to produce an answer of
*length 1,000*.

`pair_scan_two_pass` splits that in two:

1. pass one walks the pairs and computes the **best length only** -- prefix sums
   and a dictionary, no substrings at all;
2. pass two walks them again and slices only the windows whose length equals that
   best length.

| `"abab..."` | positions | slices | time | time |
|---|---|---|---|---|
| | at n = 800 | at n = 800 | at n = 500 | at n = 1,000 |
| `pair_scan` | 1,600 | 320,000 | 0.28 ms | 0.63 ms |
| `pair_scan_two_pass` | 2,400 | **800** | 0.24 ms | 0.47 ms |

The slices drop by a factor of 400 and the time drops by about 25%, for 1.5x the
positions. That is a good trade *on this shape*, and a bad one on random text
(3.03 ms against 1.59 ms), where the second pass mostly re-walks pairs in order
to collect nothing.

Two honest caveats:

* The variant only exists because the problem asks for *all* the longest
  substrings. If the contract were "return the length", pass two would not be
  needed and `pair_scan` would already be linear in copying.
* The worst case for pass two is still `Theta(n^2)` copying, when the answer
  itself is that large (`"aaaa...bbbb..."`-style inputs where many windows of the
  maximum length exist). The improvement is in the constant and in the case that
  matters -- a single long answer.

## The dominator tables

Balanced strings gave one implementation to beat. Dominators give four, with
different resources, so the interesting question changes from "how much faster"
to "which resource are you spending?" (`docs/traces/bench.txt`, `n = 100,000`,
dominator present / no dominator at all):

| implementation | positions (with / without) | time (with / without) | space |
|---|---|---|---|
| `boyer_moore` | 200,000 / 200,000 | ~8.4 ms / ~5.8 ms | `O(1)` |
| `index_cache` | 100,000 / 100,000 | ~5.3 ms / ~5.8 ms | `O(n)` |
| `sort_and_pick_middle` | 200,000 / 200,000 | ~9.6 ms / ~10.2 ms | `O(n)` |
| `divide_and_conquer` | **1,891,262** / **381,220** | ~103 ms / ~49 ms | `O(log n)` stack |

Observations:

1. **The simplest implementation is the fastest.** `index_cache` builds a
   dictionary from value to indices and reads each element exactly once
   (100,000 positions). Boyer-Moore, the famous answer, reads twice (200,000:
   vote, then verify) and spends `O(1)` memory for the privilege. Neither is
   "better"; they spend different resources, and the table says which.
2. **The divide & conquer is an order of magnitude slower, and it gets *worse*
   when a dominator exists** -- 1.89M positions against 381,220. That is
   counter-intuitive until you look at the counting rule: a candidate is counted
   over a range only when it survives a half, so with *no* dominator the counts
   fail early and whole subtrees stop, while with a dominator the candidate
   survives deeper into the tree and every level above pays for it.
3. **Sorting is competitive** because CPython's `timsort` is C and the element
   reads are the same as Boyer-Moore's (`n` for the sort plus `n` for the
   verification count). "O(n log n) loses to O(n)" is a statement about the
   constants as much as about the exponents; at `n = 10,000` the two are within
   10% of each other (939.9 us against 848.0 us).

Each of the four reads the array through a counting proxy, which is why
`positions` is a clean unit here: none of them slices, so the slice column is 0
in every dominator row -- a reminder that the metric only counts what the
algorithm is capable of doing.

## What is not measured

A measurement section that does not list its own blind spots is an advertisement,
not a lab report.

* **Memory is not measured, only reasoned about.** The space column above is
  from reading the code. A real measurement would use `tracemalloc` for heap and
  an estimate for the stack (the recursions hold ~300 bytes per frame, so
  `recursive` on a 10,000-character window wants a 3 MB stack and
  `run_deep(stack_mb=512)` is generous on purpose).
* **The counter's own overhead is not measured.** Wrapping a string in
  `ReadCounter` makes every access a Python method call; the instrument changes
  what it measures. The reads are still exact *counts*, and the timings are taken
  without the counter -- but a "reads per second" number from an instrumented run
  would be meaningless.
* **No warm-up, single machine, one Python version.** No JIT, no cache effects to
  control, but also no claim that these microseconds transfer.
* **The interpreter's per-step cost is invisible to the reads column.** That is
  the whole reason the pair scan beats the quadratic scan by 485x while reading
  *more* characters on some shapes. A metric that does not model "one interpreter
  step per loop iteration" cannot explain the difference; the timer can.
* **Nothing here is a proof.** `Theta(n^2)` counts are evidence for a shape, not
  an argument about all shapes. The proofs are in
  [`docs/01`](01-balanced-strings.md) and [`docs/02`](02-dominator.md); the
  numbers here are what convinced the code to change.

## Reproducing all of it

```console
$ python -m tools.bench --sizes 125,250,500,1000        # both problems (~1 min)
$ python -m tools.bench --balanced --sizes 100,200,400  # just the strings
$ python -m tools.bench --dominator --repeat 5          # just the dominators
$ python -m tools.make_traces                            # rewrite docs/traces/
$ python -m tools.make_traces --check                    # fail if a trace is stale
$ python -m tools.run_all                                # tests + traces + digests + tour
```

`tools/bench.py` never writes to disk (it prints), so a stray benchmark run cannot
make the committed tables disagree with the code. `docs/traces/bench.txt` is the
one trace file that is regenerated but *not* drift-checked by the test suite --
timings move between runs, and a test that fails because the laptop was busy is a
test people learn to ignore.

## Exercises

1. **Predict before you measure.** For each row of the scaling table, compute the
   expected reads from the algorithm (`n^2 / 2` for the quadratic scan on
   `"abab..."`; `1 + (sigma - 1) * n` for the pair scan on `sigma` letters) and
   compare with the measured column. Which of the two do you get exactly right,
   and where does the `+1` come from?
2. **Instrument the constant.** Add a counter inside `equal_pair` and measure how
   many 26-slot scans the quadratic scan performs at `n = 800` on `"abab..."`.
   Multiply by 26 and compare with the 320,400 positions. Which dominates? (This
   is the "invisible work" the position counter deliberately ignores.)
3. **Break your own benchmark.** The chapter already contains one shape where
   `pair_scan` loses by 20x: `"abc...z"` repeated. Explain it from the counts
   alone (`3n` for the quadratic scan against `26n` for the pair scan), then find
   the alphabet size `sigma` at which the two switch places for a fixed `n`.
   (Measure it; the answer is not `sigma = 26`.)
4. **Measure the metric.** Time `brute_force_normalized(text)` with and without a
   `ReadCounter` around the text, at `n = 100, 200, 400`. Fit the overhead per
   read. Is the instrumentation cost constant per element, or does it depend on
   the slice size?
5. **Find the crossover for the balanced problem** on random 4-letter text:
   measure at `n = 500, 1000, 2000, 4000` and report where `pair_scan` overtakes
   `brute_force`. Predict it from the examination counts first -- both are about
   `4n` there (4,373 against 4,000 at `n = 1,000` in this run), so the winner is
   decided purely by the *constants*, and no asymptotic argument can predict it.
   That is the point of the exercise.
6. **Add a memory column.** Use `tracemalloc` to compare peak allocation of the
   four quietest implementations at `n = 100,000`, and find the first `n` at which
   `index_cache` exceeds 100 MB.
7. **Make the timer honest.** Repeat every timing ten times, then report the
   minimum, the median, and the interquartile range. How much of the "1.08x
   speed-up on random text" is inside the noise? (This is the experiment that
   tells you when a table is reporting a difference and when it is reporting a
   coincidence.)
8. **Extrapolate, then check.** From the three measured sizes on `"aaaa..."`,
   predict `brute_force`'s time at `n = 10,000` and `n = 100,000`. Then measure
   `n = 10,000` (about 10 seconds) and report how close the extrapolation was.
