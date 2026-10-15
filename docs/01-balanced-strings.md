# 01 -- Balanced substrings

> *Find the longest **balanced** substring of a string, and list every distinct
> substring of that length.*

This chapter takes that sentence apart. It defines the property precisely, shows
why the greedy algorithm you already know does not apply, builds **eight**
implementations of the same contract (an oracle, a repaired double loop and a
tighter variant of it, the recursion in three spellings, and the pair scan in two
forms), dissects the bug in the submitted loop, and finishes with measured
numbers.

---

## 1. The definition, and what counts as an answer

A string is **balanced** when

1. it uses **exactly two distinct characters**, and
2. each of those two characters occurs **the same number of times**.

| string | distinct | counts | balanced? |
|---|---|---|---|
| `""` | 0 | -- | no (no characters at all) |
| `"a"` | 1 | a:1 | no (one distinct character) |
| `"ab"` | 2 | a:1 b:1 | **yes** |
| `"aabb"` | 2 | a:2 b:2 | **yes** |
| `"abab"` | 2 | a:2 b:2 | **yes** |
| `"aaaa"` | 1 | a:4 | no |
| `"aabbb"` | 2 | a:2 b:3 | no (counts differ) |
| `"aabbc"` | 3 | a:2 b:2 c:1 | no (three distinct) |

The answer is a **pair**, not a number: the length of the longest balanced
substring, *and* the sorted list of distinct substrings of that length. For
`"abcabc"` the answer is `(2, ['ab', 'bc', 'ca'])` -- three different substrings
tie at the longest length, and dropping any of them loses information the
question asked for. (One of the archived programs drops them; see section 5.)

Two edge cases are conventions rather than mathematics, and the repository
states them instead of hoping nobody notices:

* the empty string has no balanced substring, so the answer is `(0, [])`;
* a string with fewer than two distinct characters has no balanced substring
  either, so `"aaaa"` also gives `(0, [])` -- note that this is *not* the length
  of the string.

## 2. Why the greedy you already know does not work

There is a standard exercise that looks exactly like this one: *"find the
longest substring with at most two distinct characters"*, solved with a sliding
window in `O(n)`. If you reach for that window here, you get a plausible answer
that is wrong, and the reason is worth understanding.

```python
def longest_at_most_two_distinct(s):
    """The classic sliding window.  Correct -- for a different question."""
    last, left, best = {}, 0, ""
    for right, ch in enumerate(s):
        last[ch] = right
        if len(last) > 2:                    # a third letter appeared
            drop = min(last, key=last.get)   # retire the leftmost of the three
            left = last[drop] + 1
            del last[drop]
        if right - left + 1 > len(best):
            best = s[left:right + 1]
    return best
```

Run it against the oracle (`algorithms.balanced.reference`) and see:

| input | "at most two distinct" | longest balanced | same? |
|---|---|---|---|
| `'aaab'` | `(4, 'aaab')` | `(2, ['ab'])` | **no** |
| `'aabbb'` | `(5, 'aabbb')` | `(4, ['aabb'])` | **no** |
| `'aabbaa'` | `(6, 'aabbaa')` | `(4, ['aabb', 'abba', 'bbaa'])` | **no** |
| `'aaaa'` | `(4, 'aaaa')` | `(0, [])` | **no** |
| `'aabbc'` | `(4, 'aabb')` | `(4, ['aabb'])` | same length |
| `'abcabc'` | `(2, 'ab')` | `(2, ['ab', 'bc', 'ca'])` | same length |

**Why it cannot be patched.** Every sliding window rests on a monotonicity
property: *"if this window is invalid, then every window containing it is
invalid"*. For "at most two distinct characters" that is true -- adding
characters never removes one. For *balanced* it is false in both directions:

* **Extending can destroy balance:** `"aabb"` is balanced, `"aabbb"` is not.
* **Shrinking can destroy balance:** `"aabb"` is balanced, `"aab"` is not.

So when a window is unbalanced, no rule based on the window alone can tell you
whether the answer is hiding inside it or has already been left behind. The
window metaphor dies, and with it the `O(n)` hope. What survives is
*enumeration* -- look at every window, or find a structure that lets you skip
most of them. Both are in this chapter.

> **The one thing that is monotone**, and the reason the quadratic scans are not
> as bad as they look: the number of *distinct characters* in a window never
> decreases as the window grows. That is what allows the scan to stop the moment
> a third letter appears -- it is a statement about the alphabet, not about
> balance.

## 3. The oracle: `algorithms/balanced/reference.py`

```python
def reference_normalized(text):
    tracker = BestTracker()
    for start in range(len(text)):
        for end in range(start + 1, len(text) + 1):
            window = text[start:end]
            if is_balanced(window):          # counts the window, from scratch
                tracker.consider(window)
    return tracker.result()
```

Eight lines, `O(n^3)` time (O(n^2) windows, each counted in O(n)), and no
cleverness whatsoever. It exists because every other implementation in this
chapter is judged against it, and a judge that is itself clever is not a judge.

That is not a hypothetical. The first version of this file contained an
"obvious" optimisation:

```python
if len(window) > tracker.length and is_balanced(window):   # WRONG
```

It looks harmless -- why test a window that cannot beat the record? -- and it
silently drops every *additional* substring that ties with the record. It
answered `(2, ['ab'])` for `"abcabc"` instead of `(2, ['ab', 'bc', 'ca'])`, and
it did so while every other implementation was being checked against it. The
full story, and the test that caught it, is in
[`docs/04-bug-hunt.md`](04-bug-hunt.md#the-oracle-that-wasnt).

## 4. Algorithm A: the double loop, done correctly

The oracle re-counts each window from scratch. The first real improvement is to
carry the counts along as the window grows:

```
for each start:
    freq = [0] * 26 ; distinct = 0
    for each end from start to n-1:
        fold text[end] into freq
        if distinct > 2: stop            # a third letter: nothing longer can work
        if distinct == 2 and counts are equal: record text[start..end]
```

Two state variables do all the work: a 26-slot frequency table and a counter of
how many slots are non-zero. Folding in one character is `O(1)`; asking "are the
two counts equal?" is `O(26)`, which is a constant.

```python
for start in range(n):
    freq = [0] * 26
    distinct = 0
    for end in range(start, n):
        index = ord(text[end]) - ord("a")
        if freq[index] == 0:
            distinct += 1
        freq[index] += 1

        if distinct > 2:
            break                      # <- safe: distinct never shrinks

        if distinct == 2 and equal_pair(freq):
            tracker.consider_span(text, start, end)
```

`equal_pair` is the inner test, and it is written to avoid allocating:

```python
def equal_pair(freq):
    first = second = 0
    for value in freq:
        if value:
            if first == 0:
                first = value
            elif second == 0:
                second = value
            else:
                return False           # a third letter -- not a two-letter window
    return first != 0 and first == second
```

**Complexity.** For each `start` the inner loop walks to the end of the string
or to the third distinct letter, so the total number of window steps is
`O(n^2)`, and each step pays one 26-slot scan: `O(26 n^2)`, i.e. quadratic in
`n` with a constant of 26. `O(1)` extra space beyond the answers.

**Why `break` is right.** When a third letter enters the window, every longer
window starting at this `start` also contains that letter, so none of them can
be balanced (condition 1 of the definition). The `break` is a statement about
*distinct characters*, and it is valid precisely because that quantity is
monotone. If you ever find yourself writing the same `break` reasoning about
*balance*, stop -- it is false, as section 2 shows.

The window-by-window trace of this loop on `"aabbc"` -- every state variable, at
every step -- is in `docs/traces/balanced-scan.txt`. Reproduce it with:

```python
from algorithms import tracing
print(tracing.scan_table("aabbc"))
```

## 5. The submitted loop, and the one line that is in the wrong place

Here is the archived program (`algorithms/original/balanced_iterative.py`),
reindented only enough to make the shape visible:

```python
for start in range(n):
    freq = [0] * 26
    distinct = 0
    for end in range(start, n):
        idx = ord(S[end]) - ord('a')
        if freq[idx] == 0:
            distinct += 1
        freq[idx] += 1
        if distinct > 2:
            break
    if distinct == 2:                       # <-- OUTSIDE the end loop
        ...check freq, record S[start:end + 1]...
```

The balance test is dedented: it runs **once per `start`, after the `end` loop
has finished**, and `end` at that moment is the last index the scan touched.
So for each starting position the program examines exactly *one* window -- the
longest one that survived the alphabet check -- and throws away every shorter
one that might have been balanced.

### What that does to the answers

```
'aabbb'   submitted: 0 []        correct: 4 ['aabb']
'aabbc'   submitted: 2 ['bc']    correct: 4 ['aabb']
'abcabc'  submitted: 2 ['bc']    correct: 2 ['ab', 'bc', 'ca']
'aabbaa'  submitted: 4 ['bbaa']  correct: 4 ['aabb', 'abba', 'bbaa']
```

For `'aabbb'` the scan walks from index 0, sees `a a b b` (which *is* balanced),
keeps going, meets the third `b`, and stops. Only now does it ask the question,
about the window `'aabbb'` -- which is not balanced. The answer `'aabb'` was
found and discarded. Nothing is printed; the function returns `(0, [])`, which
means *"this string contains no balanced substring"* about a string that
contains one.

### Why so many inputs still work

The bug is invisible whenever every scan runs to the end of the string, because
then "the last window for this start" is the whole suffix. `'aabb'`, `'abab'`,
`'ababab'` and `'aaabbb'` are all answered correctly by the submitted program.
That is exactly what makes this class of bug dangerous: the examples an author
tests by hand are often the ones where the wrong code is right.

### The diagnosis is proven, not asserted

`tests/test_original_characterization.py` contains a ten-line model of what the
misplaced test computes -- "for each start, evaluate only the last window
touched" -- and asserts that the submission matches it on

* 20,000 random strings over `{a, b, c, d}`, and
* every string up to length 7 over `{a, b, c}` (3,280 inputs).

Matching a model on every input is a much stronger statement than "looks like
the bug", and it also says what the *fix* is, with no guesswork:

```diff
         if distinct > 2:
             break
-    if distinct == 2:
-        ...check freq and record...
+        if distinct == 2 and equal_pair(freq):
+            tracker.consider_span(text, start, end)
```

Only the indentation of the test changes. `'aabbb'` then answers
`(4, ['aabb'])`, and
`tests/test_balanced_implementations.py` checks that the repaired loop agrees
with the oracle on every short string over two, three and four letters.

### A second, quieter defect in the same block

The frequency test in both submissions reads only the **first two** non-zero
slots:

```python
for f in freq:
    if f > 0:
        if firstFreq == -1: firstFreq = f
        elif secondFreq == -1: secondFreq = f
return firstFreq != -1 and secondFreq != -1 and firstFreq == secondFreq
```

Ask it about a window with three letters whose first two counts happen to match,
and it says *balanced*:

```python
>>> legacy_equal_pair([2, 2, 1] + [0] * 23)   # three distinct letters
True
>>> equal_pair([2, 2, 1] + [0] * 23)          # the repaired version
False
```

Nothing goes wrong today only because an independently maintained `distinct`
counter short-circuits that case first. Two guards, one of which is silently
wrong, and the wrong one is one small refactor away from being load-bearing.
Bug **B1b** in [`docs/04`](04-bug-hunt.md).

## 6. Algorithm B: the recursion

The recursive submission walks the same space with two mutually recursive
functions. `TryStart(S, n, start, longest, best_list)` plays the role of the
outer loop; `TryEnd(S, n, start, end, freq, distinct, longest, best_list)` plays
the role of the inner loop, recursing on `end + 1` instead of looping.

The repaired version is in `algorithms/balanced/recursion.py`. It keeps the
recursion, fixes the placement of the test, and writes the body with a single
exit point so that the trace hook does not need a second function call per
character (that detail is worth about 500 characters of usable string length;
see [`docs/03`](03-recursion-vs-iteration.md)).

Here is the whole call tree for `"aabbb"` -- one node per `TryEnd` call, with
`(longest so far, answers so far)` after the arrow (full file:
`docs/traces/balanced-recursive-tree.txt`):

```
|-- TryEnd(start=0, end=0)  -> [4, ['aabb']]
|   `-- TryEnd(start=0, end=1)  -> [4, ['aabb']]
|       `-- TryEnd(start=0, end=2)  -> [4, ['aabb']]
|           `-- TryEnd(start=0, end=3)  -> [4, ['aabb']]
|               `-- TryEnd(start=0, end=4)  -> [4, ['aabb']]
|                   `-- TryEnd(start=0, end=5)  -> [4, ['aabb']]
|-- TryEnd(start=1, end=1)  -> [4, ['aabb']]
...
```

Reading it teaches three things at once:

* **The shape is the same triangle as the double loop.** For `start = 0` the
  chain has `n + 1` calls; for `start = 1` it has `n`; and so on. `O(n^2)`
  calls, one per window, exactly like the loops.
* **The scan stops early when it can.** The chain for `start = 1` is shorter
  than the one for `start = 0` here only by one, but on `"aabbc"` the chains
  stop the moment a third letter appears (compare the second tree in the same
  file).
* **Every frame returns the same value.** `(4, ['aabb'])` comes back out of all
  of them, because the accumulator is shared. Threading that pair up the call
  chain (which the original does) is pure ceremony -- a smell, not a bug.

The 2x2 of this repository is completed by `recursive_shared_freq`, which keeps
**one** frequency table, mutates it going down, and un-mutates it coming back
up. Same answers, no 26-integer copy per level, measurably faster:

| n = 500, input `"ababab..."` | positions | slices | best of 3 |
|---|---|---|---|
| `recursive` (copy `freq[:]` per level) | 125,250 | 62,750 | 138.7 ms |
| `recursive_shared_freq` (mutate and undo) | 125,250 | 62,750 | 101.5 ms |

From `docs/traces/bench.txt`. The two read the same number of characters -- the
difference is that one of them also copies 26 integers per call, and the columns
above cannot see that. A 10% difference for a genuinely different programming
technique is the honest result; the technique is worth learning for the *shape*
of the code, not for the speed-up.

Both recursions inherit one limitation from the shape: **depth grows with the
window**, one frame per character scanned. `"a" * 996` works; `"a" * 1000` raises
`RecursionError`. That is a property of CPython, not of the algorithm, and there
is a supported way around it (`algorithms.support.run_deep`) that this
repository uses in its tests rather than pretending the limit does not exist.

## 7. Algorithm C: the pair scan (the fast one)

The quadratic scans examine `O(n^2)` windows and get away with it because most
of them die early. On `"abababab..."` nothing ever dies, and they degrade to
their true quadratic self: 304 ms for 1,000 characters. The pair scan does it in
0.63 ms.

### The idea, in three steps

1. **A balanced substring uses exactly two letters.** With 26 letters there are
   `26 * 25 / 2 = 325` unordered pairs. Instead of asking "which window is
   balanced?", ask 325 times "which window over *this* pair is balanced?".
2. **For a fixed pair `{x, y}`, a balanced window cannot contain any other
   letter.** So collect the positions where `x` or `y` occurs and split them into
   maximal runs of *consecutive* positions -- two indices are "consecutive" only
   if no other letter fits between them. Every candidate lives inside one run.
3. **Inside a run, replace `x` with `+1`, `y` with `-1`.** A substring has equal
   numbers of `x` and `y` exactly when its sum is `0`, which happens exactly
   when two **prefix sums are equal**. So a single left-to-right pass that
   remembers the first index at which each prefix value was seen finds the
   longest zero-sum substring of the run.

Step 3 is the classic *longest subarray with sum zero* trick. Step 2 is what
makes it applicable, and step 1 is what makes it cheap.

### What it looks like when it runs

```
| pair | blocks | block sizes | best | substrings found |
| ab   |      1 | 4           |    4 | aabb             |
| ac   |      2 | 2 1         |    0 | -                |
| bc   |      1 | 3           |    2 | bc               |

best over all pairs: 4
```

`pair_scan('aabbc')`: for the pair `{a, b}` the positions are `0,1,2,3` -- one
run of length 4 -- and the prefix sums go `+1, +2, +1, 0`, which repeats `+1`
(between index 1 and 3) and `0`, giving `'aabb'`. For `{a, c}` the positions are
`0,1` then `4`: two runs, and neither can hold two of each letter. For `{b, c}`
the run is `2,3,4` with sums `-1, -2, -1`, and the repeated `-1` gives `'bc'`.
Full file: `docs/traces/balanced-pairs.txt`.

### Why no answer is missed

Claim: for a fixed pair, every balanced substring of that pair is *considered*
by the pass.

Take a balanced substring `s[i..j]` over the pair, of the best length `L`. It
lives inside one run of the pair's positions. Its prefix sums satisfy
`pre[i] == pre[j+1]`, and `i` is inside the run. Because the pass stores, for
each prefix value, the *earliest* index at which that value occurred in the run,
it visits the boundary `j + 1` and finds a start `i' <= i` with `pre[i'] ==
pre[j+1]`. If `i' < i`, then the substring `s[i'..j]` is also balanced, has
length `> L`, and lives in the same run -- contradicting that `L` is the best
length. Hence `i' == i` and the pass considers exactly `s[i..j]`.

The argument is worth reading twice: the "earliest index" choice is not a
tie-breaking convention, it is what makes the proof work.

### Complexity, and the bill nobody mentions

* 325 pairs.
* One pair costs `O(k log k)` where `k` is how many times the two letters occur
  (`O(k)` if the positions are already sorted by construction, plus the sort),
  and `O(k)` space.
* `sum over pairs of k = 25 n`, so the total is `O(26^2 * n log n)` with a small
  constant. For 26 letters that is 325 passes over the relevant positions.

Measured on `"ababab..."` (`docs/traces/balanced-scaling.txt`):

| n | pair scan: positions | brute_force: positions |
|---|---|---|
| 100 | 200 | 5,050 |
| 200 | 400 | 20,100 |
| 400 | 800 | 80,200 |
| 800 | 1,600 | 320,400 |

Each doubling of `n` doubles the pair scan's search work and quadruples the
quadratic scan's. That is the complexity class, measured rather than asserted.

**The bill**: the same table shows the pair scan copying 320,000 characters at
`n = 800` to *materialise* its improving answers -- quadratic copying, because
the records get longer as the algorithm goes. It is still about 280x faster in
wall-clock time at `n = 500` (77 ms versus 0.28 ms), because copying characters
is a `memcpy` in C while the quadratic scan spends a Python bytecode per
character -- but the bill is real, and conflating "search work" with "copying
work" is how performance tables start lying. [`docs/05`](05-complexity-lab.md) is the full discussion,
including the measurement that forced this repository to split the metric in two.

**Honesty note.** `O(26^2 * n log n)` is not the last word, and the repository
does not pretend otherwise.

* The idea behind the pair scan -- encode "these two letters occur equally often"
  as an equality of two prefix sums and look up the earliest occurrence of each
  value -- is the standard linear-time technique for this problem. The same
  construction with a *two*-dimensional key (the pair of count differences) solves
  "exactly three distinct, each equally often" in one linear pass; you can see it
  in the editorial for LeetCode 3714, *Longest Balanced Substring II*.
* Generalising the key to `k - 1` count differences gives "exactly `k` distinct,
  all equally often" in one linear pass **per subset of letters**: 325 passes for
  pairs, 2,600 for triples, `C(26, k) * n` in general. That is why the pair scan
  is described as `O(26^2 * n)` work in the complexity table rather than
  `O(n)`: the constant is the whole story.
* The nearest published results we could find are narrower than the problem.
  LeetCode 3714, *Longest Balanced Substring II*, caps the alphabet at three
  letters and solves that case in one pass with the prefix-difference idea above;
  the two-letter case is the same idea with one difference instead of two. For
  the unrestricted alphabet -- all 26 letters, `C(26, k)` subsets -- no
  construction in that style turned up while writing this chapter, so `pair_scan`
  here is this repository's own. The phrase to search for is *longest well-balanced
  substring*; if you find an unrestricted linear-time algorithm, the useful thing
  to bring back is not the algorithm but its oracle -- and `reference` above is
  one.

## 8. The eight implementations, side by side

| function | time | space | role |
|---|---|---|---|
| `reference` | `O(n^3)` | `O(n)` | the oracle; obviously correct by construction |
| `brute_force` | `O(26 n^2)` | `O(1)` | the repaired submission |
| `brute_force_incremental` | `O(n^2)` | `O(1)` | the same, with an `O(1)` balance test |
| `round_trip` | `O(26 n^2)` | `O(1)` | the recursion unrolled into loops |
| `recursive` | `O(26 n^2)` calls | `O(n)` stack | the repaired recursion (`freq[:]` per level) |
| `recursive_shared_freq` | `O(26 n^2)` | `O(n)` stack | backtracking: mutate, recurse, undo |
| `pair_scan` | `O(26^2 n log n)` | `O(n)` | 325 letter pairs + prefix sums |
| `pair_scan_two_pass` | `O(26^2 n log n)` | `O(n)` | the same search, copying only the answers |

All eight return `(length, sorted_substrings)` and all eight agree on every
tested input. That is checked exhaustively for small alphabets and randomly for larger
ones in `tests/test_balanced_implementations.py`.

`round_trip` is not redundant: it is the mechanical unrolling of the recursion
into loops, and writing it is the best way to see that the two submitted
programs are two spellings of one algorithm.
[`docs/03`](03-recursion-vs-iteration.md) does the translation line by line.

## 9. Performance, honestly

From `docs/traces/bench.txt` (this machine; see
[`docs/05`](05-complexity-lab.md) for how these were taken and why you should
expect different absolute numbers):

| input shape | n | `brute_force` | `pair_scan` | `pair_scan_two_pass` | speed-up |
|---|---|---|---|---|---|
| random, 4 letters | 1000 | 1.72 ms | 1.59 ms | 3.03 ms | 1.08x |
| `"ababab..."` | 1000 | 304 ms | 0.63 ms | 0.47 ms | **485x** |
| `"aaaa..."` | 1000 | 46.7 ms | 53 us | 54 us | **880x** |

Four things to notice, in order of importance:

1. **The fancy algorithm is not always much faster.** On random 4-letter input
   almost every window dies at the third letter, so the quadratic scan only does
   about 4n steps instead of `n^2 / 2` -- and the pair scan's fixed 325-pair
   overhead is comparable. An 8% speed-up is not the story you would tell if you
   only tested this shape (a lesson in its own right: `n = 1,000` random text is
   a *small* input as far as this problem is concerned).
2. **Adversarial input is where complexity classes bite.** Two letters, never a
   third, and the quadratic scan has no shortcut left: 485x.
3. **A single letter is the quadratic scan's nightmare.** Nothing ever dies and
   nothing is ever balanced: 880x for a string that has no answer at all.
4. **The two-pass variant is the fastest of all on the adversarial shapes** --
   0.47 ms against 0.63 ms on `"abab..."` -- and the *slowest* on random text,
   because it walks the pairs twice and the second walk finds almost nothing to
   do. `docs/05` is where that trade-off is taken apart.

## 10. Three design notes carried by this package

**`BestTracker` is the accumulator.** Keeping "best length so far + the set of
substrings achieving it" in one object is what lets the recovery of the
submissions stay readable: the recursion passes the tracker down instead of
threading two values back up through every frame, and the loop version looks
like the loop version. It also gives one place for the "collect ties, dedupe"
rule, which both submissions implemented by hand in slightly different ways.

**`consider_span` exists because of a measurement.** The first version of the
quadratic scan called `tracker.consider(text[start:end+1])`, which builds the
substring before the tracker can decide whether it is interesting. On
`"abab..."` there are `Theta(n^2)` balanced windows, so building all of them
cost `Theta(n^3)` -- the scan was quadratic and the *program* was cubic. One
`if` fixed it: 10,604,500 element reads became 188,000 at `n = 500` (a 56x
reduction, and 188,000 = 125,250 positions + 62,750 characters of answer).
Nothing
about the algorithm changed; only the decision of *when* to build the answer.
The benchmark table that hid the problem, and the fix, are in
[`docs/05`](05-complexity-lab.md#the-measurement-that-changed-the-code).

**Sorted output is part of the contract.** The submissions returned answers in
the order their loops happened to find them, which makes two correct
implementations look different. Sorting is free here (the answer set is small)
and makes every implementation directly comparable to every other -- including
in tests, where list order would otherwise turn a correctness check into an
ordering argument.

## 11. Exercises

1. **Patch the greedy.** For `'aaab'` the at-most-two-distinct window says 4 and
   the truth is 2. Characterise exactly which inputs make the greedy
   under-report, then check your characterisation against the oracle over all
   strings up to length 10.
2. **Count the windows.** Prove that the repaired double loop examines at most
   `n(n+1)/2` windows, and that it examines exactly that many on `"aaaa..."`.
3. **Tighten `equal_pair`.** Can "counts equal" be maintained incrementally
   (in `O(1)` per step instead of `O(26)`)? What state would you need? Is it
   worth it? Measure before answering.
4. **Break the pair scan behind its back.** Try to construct an input on which
   the pair scan's slice bill exceeds its position count by more than 100x.
   (`"ababab..."` achieves 200x at `n = 800`. Can you do better? Can you do
   *worse* for the quadratic scan?)
5. **Return only the length.** Modify `pair_scan` to return just the best
   length. How much does the slice column fall? (Hint: it should be `O(n)`.)
   Does it change the answer's asymptotic cost when the contract *does* require
   the substrings?
6. **Two-pass answer collection.** Collect the answer strings only after the
   best length is known, by making a second pass and slicing only windows of
   that exact length. Verify that the answers are identical, count the reads,
   and explain why the worst case is still `Theta(n^2)` when the output itself
   is that large. (Done, for comparison purposes:
   `algorithms/balanced/fast.py::pair_scan_two_pass`, measured in `docs/05`.)
7. **Generalise.** `k`-balanced: exactly `k` distinct characters, each equally
   often. What does the double loop need to change? What happens to the
   `distinct > 2` short-circuit? What does the pair-scan decomposition become?
   (This one is genuinely harder -- there are `C(26, k)` subsets.)
8. **Prove the tie.** Find the shortest string whose answer contains three
   different substrings of the maximal length. Is `'abcabc'` (answer length 2,
   three answers) optimal?
