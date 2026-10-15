# 04 -- Bug hunt

This is the catalogue: every defect found in the four submitted programs, with a
reproduction you can run, the reason it happens, the fix, and the test that keeps
it fixed. Then it is the *method*: how these were found, which techniques paid
off, and which hunches turned out to be wrong.

Files under `algorithms/original/` are frozen. Their SHA-256 digests are recorded
in `algorithms/original/FROZEN.sha256` and checked by the test suite, so a claim
in this chapter cannot drift away from the code it describes. If you want to
experiment, copy the file -- do not edit the archive.

**How to reproduce everything in this chapter:**

```console
$ python -m tools.demo --scoreboard                       # the one-line summary
$ python -m unittest tests.test_original_characterization -v   # 20,000 fuzz cases
$ python -m tools.make_traces                             # regenerate the traces
```

(You will see `Error: only lowercase letters allowed.` print itself while the
suite runs. That is bug B2 doing in the test output exactly what it does in
production.)

---

## 0. The scoreboard

Eighteen entries are catalogued below: **two change answers silently** (B1,
B12), **one is a wrong test that another guard happens to cover** (B1b), **two
crash** on plausible input (B3, B4), **four are policy, contract or consistency
problems** (B2, B5, B7, B8), and **nine are the cost of getting to the next
reader** -- performance, structure, hygiene. Four programs, eighteen findings -- which is a normal ratio for
student code that has never been reviewed, and the reason the review is worth
doing.

| program | correct? | fails on | severity |
|---|---|---|---|
| balanced, loop | **no** | any scan that dies before the end of the string | silent wrong answer |
| balanced, recursion | yes | non-ASCII letters; strings longer than ~996 | crash |
| dominator, loop | yes | nothing but the input policy | contract mismatch |
| dominator, recursion | yes* | arrays containing `None` | silent wrong answer |

The rest of this chapter explains each line.

---

## B1 -- The balance test is outside the loop (critical)

**Where:** `algorithms/original/balanced_iterative.py`, the `if distinct == 2:`
block, which sits **at the same indent level as the `for end` loop** instead of
inside it. (Its body is still indented as if it were inside the loop -- the
fossil of the move.)

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
        if distinct == 2:                 # <-- same level as `for end`
                firstFreq = -1            # (and the body kept its old indent)
                ...
                if length > longest: ...
                elif length == longest: ...
    return longest, longest_list
```

**Symptom:** the program answers `(0, [])` for `'aabbb'`, whose longest balanced
substring is `'aabb'`; `(2, ['bc'])` for `'aabbc'` where the answer is
`(4, ['aabb'])`; and it drops tied answers on `'abcabc'` and `'aabbaa'`.

**Why:** the loop mutates `freq` and `distinct` for every window, then throws
them away. Only after the scan finishes does it ask the question, about the
single window `S[start:end+1]` -- the last one it touched, which is the longest
one the alphabet check allowed. Every shorter window is discarded unexamined.

**Reproduction:**

```python
>>> from algorithms.original import balanced_iterative as submission
>>> submission.LBS_all_longest("aabbb")
(0, [])
>>> from algorithms import balanced
>>> balanced.reference("aabbb")
(4, ['aabb'])
```

**Proof, not opinion.** `tests/test_original_characterization.py` contains a
model of the misplaced check -- "for each start, evaluate only the last window
touched" -- and asserts the submission matches it on 20,000 random strings over
`{a, b, c, d}` and on all 3,280 strings of length at most 7 over `{a, b, c}`.
`docs/traces/balanced-scan.txt` shows every window of the corrected scan on the
same inputs, which is what the submission would have seen if it had asked more
often.

**Fix:** move the test inside the loop.

```diff
         if distinct > 2:
             break
-    if distinct == 2:
-        firstFreq = -1
-        ...
-            if length > longest:
-                longest = length
-                longest_list = [substring]
+        if distinct == 2 and equal_pair(freq):
+            tracker.consider_span(text, start, end)
```

`algorithms/balanced/iterative.py` is the fixed version, and it is checked
against the oracle on every string up to length 10 over two letters, length 8
over three letters and length 6 over four.

**Why it survived:** on `'aabb'`, `'abab'`, `'ababab'` and `'aaabbb'` the buggy
version is *correct* -- for those inputs every scan runs to the end of the
string, so the "last window" is the whole suffix, and the interesting window is
in there. Bugs that hide behind the examples you try by hand are the expensive
kind. (`tests/test_contracts.py::TestBalancedContract::test_it_is_right_when_every_scan_runs_to_the_end`
is the regression test for exactly this class of input.)

**How wrong is it, in aggregate?** Exhaustively, over every string of length at
most 7 on `{a, b, c}`:

| strings over `{a, b, c}` up to length | wrong answers | rate |
|---|---|---|
| 5 | 270 of 364 | 74.2% |
| 6 | 846 of 1,093 | 77.4% |
| 7 | 2,694 of 3,280 | **82.1%** |

and 1,152 of the 1,365 strings of length at most 5 over `{a, b, c, d}` (84.4%).
The examples that work are the exception, not the rule; the program is right on
the inputs whose scans all run to the end of the string, and everything else is
a coin flip that landed on silence.

---

## B1b -- The frequency test does not check what it claims (latent)

**Where:** the same block, in both submissions.

```python
firstFreq = -1
secondFreq = -1
for f in freq:
    if f > 0:
        if firstFreq == -1:
            firstFreq = f
        elif secondFreq == -1:
            secondFreq = f
return firstFreq != -1 and secondFreq != -1 and firstFreq == secondFreq
```

**Symptom:** none today -- and that is the problem. The loop stops recording
after the first two non-zero slots, so it answers "balanced" for a window that
contains **three** letters if the first two counts happen to be equal:

```python
>>> from algorithms.balanced.core import legacy_equal_pair, equal_pair
>>> legacy_equal_pair([2, 2, 1] + [0] * 23)   # a:2 b:2 c:1 -- three letters!
True
>>> equal_pair([2, 2, 1] + [0] * 23)          # the repaired version
False
```

**Why nothing breaks:** an independently maintained `distinct` counter is
checked first (`if distinct == 2`), and it is always right. The two tests agree
on every input that reaches them, so the weaker one never matters.

**Why it is still a bug report:** two guards for one condition, one of which is
silently wrong. Delete the first -- a plausible "simplification", since the
frequency test looks like it covers the same ground -- and the program starts
accepting three-letter windows. The fix is to reject a third non-zero slot, and
the test suite now asserts the difference between the two functions directly
(`tests/test_balanced_core.py::TestEqualPair::test_the_submitted_version_is_weaker`).

---

## B2 -- Input policy by `print` (design)

**Where:** the first lines of `LBS_all_longest`.

```python
for ch in S:
    if not ('a' <= ch <= 'z'):
        print("Error: only lowercase letters allowed.")
        return 0, []
```

**Symptom:** `LBS_all_longest("AAbb")` prints a message to stdout and returns
`(0, [])`. A caller that does not watch stdout cannot tell that answer apart from
"there is no balanced substring" -- and `(0, [])` is a legitimate value for a
legitimate input.

Three separate problems in four lines:

* **The failure channel is wrong.** A library function that cannot do its job
  should raise. Printing is for programs, and this is not one.
* **The return value is a lie.** `(0, [])` is a valid answer, so the error path
  is indistinguishable from success.
* **It disagrees with its sibling.** The recursive submission accepts uppercase
  (it lower-cases the input) and returns the right answer. Two programs for the
  same problem, two policies, no documentation.

**Fix:** pick one policy and raise. This repository accepts ASCII letters,
folds case, and raises `ValueError` for anything else, with the offending
character and its index in the message:

```python
>>> from algorithms.balanced.core import normalize
>>> normalize("AaBb")
'aabb'
>>> normalize("ab1c")
Traceback (most recent call last):
    ...
ValueError: only ASCII letters are allowed; found '1' at index 2
```

**Test:** `tests/test_contracts.py::TestBalancedInputPolicy` asserts the old
policy, the sibling's policy and the new policy side by side, so the difference
is visible rather than implied.

---

## B2b -- The duplicate check is a linear scan (performance)

**Where:** `LBS_all_longest`, when recording an answer.

```python
elif length == longest:
    duplicate = False
    for old in longest_list:
        if old == substring:
            duplicate = True
            break
    if not duplicate:
        longest_list.append(substring)
```

Comparing a new string against every answer already recorded, when the question
is "have I seen this before?". A `set` answers it in constant time, and the
comparison itself walks both strings.

**Fix:** `BestTracker` in `algorithms/balanced/core.py` keeps the answers in a
`set` and sorts once at the end. The measured effect is small -- the answer list
is short in practice -- but the pattern is worth noticing because the same
construct (`for x in xs: if x == y: seen = True`) appears in student code for
problems where the list *is* long.

---

## B2c -- The answer is pasted together one character at a time (performance)

**Where:** `LBS_all_longest`, when a window is accepted.

```python
substring = ""
for i in range(start, end + 1):
    substring += S[i]
```

**Symptom:** not a wrong answer -- a slow one, and a slow one *in the worst
place*. `+=` on a string allocates a new string and copies both halves, so
building a window of length `L` costs `O(L)` character copies **per character**,
i.e. `O(L^2)` for the build alone. On `"ababab..."` at n = 500 the archived loop
pastes 62,750 characters together this way: the same volume as the corrected
version's slices, but paid one Python-level concatenation at a time instead of
one `memcpy`.

| input (n = 500) | windows built | characters pasted | `n^2/2` for comparison |
|---|---|---|---|
| `"ababab..."` | 250 | 62,750 | 125,000 |
| `"aabbaabb..."` | 125 | 31,500 | 125,000 |
| `"aaaa..."` | 0 | 0 | 125,000 |
| random over `{a,b,c,d}` | 0 | 0 | 125,000 |

The two right-hand rows are the interesting ones: this cost is *zero* on the
inputs where the balance test never fires, which is why it hides so well.

**Fix:** slice. `S[start:end + 1]` is one C-level copy, and
`BestTracker.consider_span` delays even that until the window can win. The
`+=`-in-a-loop idiom is worth a lint rule of its own: it is the single most
common accidental quadratic in beginner Python, and the fix is always shorter
than the bug.

---

## B3 -- `isalpha()` is not `is an ASCII letter` (crash)

**Where:** `algorithms/original/balanced_recursive.py`, inside `TryEnd`.

```python
if not S[end].isalpha():
    return longest, best_list
index = ord(S[end]) - ord('a')
...
freq[index] += 1          # IndexError for index >= 26
```

**Symptom:**

```python
>>> from algorithms.original import balanced_recursive as submission
>>> submission.LBS("caf\u00e9")           # "café" with a real é
IndexError: list index out of range
```

**Why:** `'é'.isalpha()` is `True` -- in Python, `str.isalpha` means "is a letter
of some alphabet", not "is one of the 26 letters this program supports". The
guard lets it through, `ord('é') - 97` is `136`, and `freq[136]` is out of range
for a 26-slot list. (`'Straße'` crashes the same way on the `ß`.) The same input
is rejected cleanly by the loop submission, which checks `'a' <= ch <= 'z'` --
so the two submissions disagree about what a valid input even is.

Two ways to fix, and the repository takes the explicit one:

```python
if "a" <= ch <= "z":        # or "A" <= ch <= "Z" when case-folded
    ...
else:
    raise ValueError(f"only ASCII letters are allowed; found {ch!r} at index {index}")
```

**Test:** `tests/test_original_characterization.py::TestRecursiveSubmissionBalanced::test_non_ascii_letters_crash_it`
asserts both the `True` from `isalpha` and the `IndexError`, so the diagnosis is
documented rather than described.

---

## B4 -- Recursion depth grows with the input (crash)

**Where:** the shape of `TryStart` / `TryEnd` -- one frame per character.

**Symptom:** `LBS("a" * 1000)` raises `RecursionError`. Measured directly, the
wall is **996** characters (`"a" * 996` survives, `"a" * 997` raises) on
CPython's default limit of 1000 -- and it is 996 for the archived program, for
the repaired `recursive` and for `recursive_shared_freq` alike, because the depth
belongs to the *shape* of the algorithm, not to the bug.

(One warning about measuring this: the number you get depends on how many frames
are already on the stack when the call starts. A binary search that calls through
a helper function reports 995. That one-frame sensitivity is itself the lesson of
[`docs/03`](03-recursion-vs-iteration.md) -- the number of frames per level is
part of the capacity, and so is the number of frames under you.)

**Why:** each `TryEnd` call scans one character further and calls itself. There
is no tail-call optimisation in Python, so the frames accumulate: the depth is
`(characters scanned) + 1`, not `log n`. The companion chapter
([`docs/03`](03-recursion-vs-iteration.md)) has the measurements, the fix that
keeps the recursion (a loop for the outer `start`), and the two ways to go deeper
safely.

**Why it is a real bug and not a nitpick:** the function's own docstring-shaped
contract ("give me the longest balanced substring") says nothing about inputs
under a thousand characters. A caller with a 5,000-character string gets a hard
failure and no explanation.

**Fix and test:** `algorithms/balanced/recursion.py` uses one frame per character
of the *window* (not of the string), and
`tests/test_recursion.py::TestTheLimitIsReal` asserts the wall on both the
archived and the repaired version, so nobody can claim the repair bought depth
it did not buy.

---

## B5 -- Non-letters silently end the scan (policy)

**Where:** the same guard, seen from the other side.

```python
if not S[end].isalpha():
    return longest, best_list        # give up on this start, say nothing
```

**Symptom:** `LBS("ab1ab")` returns `(2, ['ab'])`. A digit in the middle of the
input stops every scan it touches, and the caller is never told that the string
was not fully searched.

**Why it is the mildest bug in the catalogue:** for *this* problem it costs no
correctness. A balanced substring uses exactly two distinct **letters**, so a
balanced window can never contain a non-letter -- scanning past one would be
wasted work. `tests/test_original_characterization.py` proves the equivalence:
on 2,000 random strings over `{a, b, c, 1, ., !}` the submission's answers are
exactly "solve each maximal run of letters and take the best".

So the defect is not the answers, it is the **silence**: a typo in the input
becomes a quietly smaller answer, and the caller has no way to know. The
repository's policy is to raise (`ValueError`) -- loud, cheap, and it turns a
silent class of mistakes into a stack trace.

---

## B6 -- Threading the accumulator through every frame (smell)

**Where:** `TryEnd`'s signature and return.

```python
def TryEnd(S, n, start, end, freq, distinct, longest, best_list):
    ...
    return TryEnd(S, n, start, end + 1, freq[:], distinct, longest, best_list)
```

Eight parameters, and every one of the `O(n^2)` calls returns the same
`(longest, best_list)` pair it was handed -- visible at a glance in
`docs/traces/balanced-original-tree.txt`, where every node ends with the same
`-> [4, ['aabb']]`.

This is not incorrect, it is *structural noise*: the accumulator belongs to the
whole search, not to a level of it, and threading it through the recursion makes
the recursion harder to read, the call tree harder to interpret, and the
translation to a loop harder to do mechanically. One shared `BestTracker`
(library version) removes four parameters and the whole return-value ceremony.

**Rule:** thread state that differs per level; share state that is a property of
the search.

---

## B7 -- The two programs disagree about `None` (inconsistency)

```python
>>> balanced_iterative.LBS_all_longest(None)
(0, [])
>>> balanced_recursive.LBS(None)
AttributeError: 'NoneType' object has no attribute 'lower'
```

One program treats "no string" as "empty string", the other raises
`AttributeError` from an attribute access on `None` -- an error message that says
nothing about the caller's mistake. Neither is unreasonable; having both in the
same assignment is the defect.

**Fix:** one policy (`None` means the empty string, documented in
`algorithms/balanced/core.normalize`) plus `TypeError` for non-string input,
which is what the library does:

```python
>>> balanced.reference(None)
(0, [])
>>> balanced.reference(42)
Traceback (most recent call last):
    ...
TypeError: expected str or None, got int
```

---

## B8 -- `-1` as "no dominator" (contract)

**Where:** `algorithms/original/dominator_iterative.py`.

```python
if actual_count > N // 2:
    return index
else:
    return -1
```

The algorithm is **correct** -- Boyer-Moore plus verification, `O(n)` time and
`O(1)` memory, with the index list collected during the verification pass. The
problem is the return type: the function returns either a list of indices or the
integer `-1`, so every caller must remember the magic value, and a caller who
forgets gets `TypeError: 'int' object is not iterable` at some later point.

Its sibling returns `[]` for the same situation, which is worse: `[]` is a
perfectly good list, so a caller that iterates it gets an empty loop instead of
an error, and the failure is silent.

**Fix:** one result type for both. `Dominator(value, indices) | None` removes the
question, and `algorithms/original/adapters.py` shows how to wrap the old
functions so the comparison is fair without pretending the old code was fine.

---

## B9 -- Dead code, and how to prove it (maintenance)

**Where:** `find_dominator_recursive`.

```python
left_count = sum(1 for i in range(left, right + 1) if A[i] == left_candidate) if left_candidate is not None else 0
```

`left_count` is assigned and never read -- the following ten lines recompute the
same count into a different variable. This is a fossil of an earlier draft (a
`left_count`/`right_count` comparison that was replaced by the two explicit
blocks below it).

Proving it is not a matter of squinting. The test suite walks the module's AST:

```python
def _named_loads(self, module, name):
    tree = ast.parse(inspect.getsource(module))
    stores = loads = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            if isinstance(node.ctx, ast.Store): stores += 1
            elif isinstance(node.ctx, ast.Load): loads += 1
    return stores, loads

stores, loads = self._named_loads(legacy_dc, "left_count")
self.assertEqual(stores, 1)
self.assertEqual(loads, 0)
```

Static analysis in a test is a nice habit: it settles "is this line doing
anything?" without a code review, and it fails loudly if the line becomes live
again.

---

## B10 -- Indices rebuilt at every level (performance)

**Where:** `find_dominator_recursive`, where each recursive call returns
`(candidate, indices_of_candidate_within_this_range)`.

Every node of the recursion tree walks its own range to collect indices, and then
almost every node's answer is discarded by its parent. The candidate is what
propagates; the indices are recomputed from scratch at each level.

**Cost:** `O(n log n)` element comparisons with a large constant. Measured on
`n = 100,000` with a dominator present (`docs/traces/bench.txt`; the same table
also shows the easier no-dominator case -- easier because the counts fail early
and whole subtrees stop):

| implementation | positions read | time |
|---|---|---|
| `boyer_moore` | 200,000 | ~8.5 ms |
| `divide_and_conquer`, dominator present | 1,891,262 | ~103 ms |
| `divide_and_conquer`, no dominator present | 381,220 | ~49 ms |

**Fix:** let the recursion compute the *candidate* only (the sentinel is private
to the module), and collect the indices once, at the top, in the single pass that
also verifies. `algorithms/dominator/divide.py` and
`algorithms/dominator/vote.py` both do it that way.

---

## B11 -- Three copies of the same counting loop (structure)

**Where:** `find_dominator_recursive` -- once for the "halves agree" case, once
for `left_candidate`, once for `right_candidate`.

```python
count = 0
indices = []
for i in range(left, right + 1):
    if A[i] == left_candidate:
        count += 1
        indices.append(i)
```

The repository's version extracts one `_count(a, value, lo, hi)` helper, and the
three call sites say what is *different* about them instead of repeating what is
the same. That is not cosmetic: the three copies are the reason B9 survived --
when the same logic exists three times, a fossil of an earlier draft can hide
inside one of them for a long time.

---

## B12 -- `None` as both a marker and a value (silent wrong answer)

**Where:** every `return (None, [])` in `find_dominator_recursive`.

**Symptom:**

```python
>>> dominator_recursive.find_dominator_indices([None, None, 1])
[]
```

The array `[None, None, 1]` **has** a dominator: the value `None`, occurring
twice in three elements. The program answers "no dominator", because `None` is
its internal marker for exactly that.

**Why it is worse than it looks:** the bug appears and disappears with the input
size.

```python
>>> dominator_recursive.find_dominator_indices([None, None])
[0, 1]                       # accidentally right: the base case never consults the marker
>>> dominator_recursive.find_dominator_indices([None, None, 1])
[]                           # wrong
>>> dominator_recursive.find_dominator_indices([None, None, None, 1])
[]                           # wrong
```

A tester who tries the two-element case concludes the function is fine.

**Fix, three patterns that all work:**

1. a private unique sentinel, compared by identity: `_NOTHING = object()`,
   `if candidate is _NOTHING`;
2. a two-part result: `(found, value)`;
3. a distinct result type: `Dominator(value, indices) | None`.

This repository uses (1) inside the modules and (3) at the API boundary, and
`tests/test_dominator_implementations.py::TestNoneAsAValue` pins the behaviour
for `[None, None, 1]` on all four implementations.

---

## B13 -- The redundant wrapper check (tidiness)

**Where:** `find_dominator_indices`.

```python
value, indices = find_dominator_recursive(A, 0, len(A) - 1)
if indices:
    return indices
return []
```

The `if indices` test can only be true when the indices are non-empty, and the
inner function already guarantees that its return value is either a non-empty
list or `[]`. So the wrapper re-checks the inner contract -- and, worse, it
encodes a second, independent idea of what "no dominator" looks like. When B12
is fixed, this line is the second place that has to change, and the compiler will
not tell you.

**Fix:** let the result type carry the meaning (`Dominator | None`), and delete
the wrapper's logic.

---

## B14 -- A comment that describes a different program (documentation)

**Where:** the bottom of `dominator_recursive.py`.

```python
A = [2]
print(find_dominator_indices(A))  # Output: [0, 2, 4, 6, 7] (index of dominator element 3)
```

The program prints `[0]`. The comment describes the answer for
`[3, 1, 3, 2, 3, 4, 3, 3]`, an array that appears nowhere in the file, and talks
about "dominator element 3" while the array holds only `2`. Somebody edited the
array, ran it, and pasted the output next to the stale comment -- or edited the
comment and never re-ran.

Two minutes of care for the reader who finds this file next. It is listed as a
bug because a comment that lies is a bug: it is documentation that has been
tested by nobody. The repository's answer is
`tests/test_original_characterization.py::TestRecursiveSubmissionDominator::test_the_driver_at_the_bottom_prints_a_misleading_comment`,
which prints the actual value next to the comment's claim.

---

## B15 -- Driver code at import time (packaging)

**Where:** all four files end with top-level statements that read standard input.

```python
A = [2]
print(find_dominator_indices(A))
```

and

```python
user_input = input("Enter a lowercase string: ")
length, longest_substrings = LBS_all_longest(user_input)
```

Consequences, all of which were felt while writing this repository:

* the module cannot be imported without running the driver (the ones that call
  `input()` block waiting for a keystroke);
* it cannot be tested, reasoned about, or reused;
* running the test suite prints stray output ("Error: only lowercase letters
  allowed.") from imported modules doing work at import time.

**Fix:** one line, the guard that every Python file with a driver needs.

```python
if __name__ == "__main__":
    ...
```

The archived files have exactly this change and nothing else. It is the only
modification in `algorithms/original/`, it is documented here, and the digests in
`FROZEN.sha256` were taken *after* it -- which is itself a small lesson in
knowing what your baseline is.

---

## How the bugs were found

Nine techniques, roughly in order of how much they contributed:

**1. Read the code twice: once for what it does, once for what it claims.**
B1 was found by asking "where does `freq` get used?" and noticing that the only
read of `freq` happens after the loop that fills it. B14 fell out of the same
pass.

**2. Run the examples in the assignment.** The four examples in the submission
are `[1,2,3,4]` for the dominator and one interactive run for the balanced
programs. Running the *good* examples (`'aabbb'`) is what exposed the loop
version; the assignment's own examples were all inputs the buggy program
happened to answer correctly.

**3. Build an oracle, then a differential test.** The oracle (`reference`) is
about thirty lines of code; the differential test is a nested loop. Together
they turned "I think this is wrong" into a counterexample. This is the
highest-yield technique in the catalogue and it takes twenty minutes.

**4. Model the suspected bug, and compare the model.** B1 stopped being a
suspicion when a twenty-line model of the misplaced check reproduced the
submission on 20,000 random inputs, plus every short string. A model is also a *testable hypothesis*: when it fails
to match, you have learned that your diagnosis is wrong -- cheaper than
half-fixing code on a hunch.

**5. Enumerate small inputs exhaustively.** Every string over two letters up to
length 10, over three letters up to length 8, four letters up to length 6. Small
alphabet, small length, no random seed, no flakiness, and every structural case
(a third letter, a gap, a tie) appears.

**6. Fuzz with shapes you would not write by hand.** `'aabbb'`, `'ababab...'`,
`'aaaa...'`, `'abcabc'`, strings mixing `None` values, repeated letters, one
letter. Adversarial shapes find different bugs from random ones.

**7. Patch the module at run time and look at the calls.**
`tracing.original_call_tree` replaces `TryStart`/`TryEnd` with wrappers,
exploiting the fact that Python resolves module globals at call time. No edit to
the archived file, and the call tree in
`docs/traces/balanced-original-tree.txt` is the real thing. (It also restored the
module in a `finally` block, which is the part people forget.)

**8. Count operations instead of guessing about performance.** `ReadCounter`
turned "the pair scan is faster" into "1,600 positions versus 320,400". It also
found a bug *in this repository's own code* -- see below.

**9. Static analysis.** The `ast` module settled B9 in twelve lines.

### Techniques that did not pay off here

* **Rewriting from scratch.** The temptation to write "the correct version" and
  compare outputs hides the *reason* for the difference; the model-based
  approach (4) is the same effort and yields an explanation.
* **Reading the assignment sheet again.** The sheet specifies the problem, not
  the input policy, which is why B2/B5/B7 are policy bugs: no amount of
  rereading resolves them, and the honest fix is to *decide* and write it down.
* **Micro-benchmarking first.** The most interesting performance finding
  (the quadratic copying bill of section 5 of
  [`docs/01`](01-balanced-strings.md)) does not show up in wall-clock time at
  all -- it hides behind `memcpy` and only appears when you count characters.

### The oracle that wasn't

The section exists because this repository made the mistake it warns about.
While writing `algorithms/balanced/reference.py`, this looked obviously right:

```python
if len(window) > tracker.length and is_balanced(window):    # WRONG
    tracker.consider(window)
```

A window that cannot beat the record cannot matter -- except that the contract
asks for *every* substring of the maximum length, so a window that **ties** with
the record matters enormously. The buggy oracle answered `(2, ['ab'])` for
`'abcabc'` instead of `(2, ['ab', 'bc', 'ca'])`, and it was the thing every other
implementation was being tested against.

What caught it: an *exhaustive* differential test (technique 5), because
`'abcabc'` is exactly the kind of input a random fuzzer rarely lands on
(three letters, two of them tying). What it cost: every implementation that
"disagreed with the oracle" had to be re-checked once the oracle was fixed --
all but one were right, and one (`round_trip`) had inherited the same
short-circuit pattern from the recursive source it was translated from.

Three lessons, in order of usefulness:

1. **An oracle must be dumb.** Any optimisation in it is a hypothesis that the
   rest of the suite now depends on.
2. **Exhaustive tests over small alphabets find tie bugs** that random tests miss.
3. **When N implementations disagree with your oracle, suspect the oracle** --
   four-against-one is evidence about the one.

---

## A short taxonomy

The eighteen entries sort into seven classes, and the classes are more useful
than the individual entries:

| class | bugs | tell |
|---|---|---|
| **Control-flow placement** | B1 | correct idea, wrong scope: "where" instead of "what" |
| **Weaker test than the comment claims** | B1b, B9 | two guards for one condition, or a guard nobody consults |
| **Crash on unconsidered input** | B3, B4, B7 | `isalpha`, depth, `None` -- boundaries the author never crossed |
| **Silent policy** | B2, B5 | output instead of an exception; a decision that is not written down |
| **Sentinel collision** | B12 | a real value doubling as "nothing" |
| **Accidental quadratic** | B2c | `+=` in a loop, a slice where a concatenation was |
| **Structure and hygiene** | B2b, B6, B8, B10, B11, B13, B14, B15 | the code works; the next reader pays |

The severity ordering used throughout this chapter is not "how hard is it to
fix" but **how long does it take to notice**:

1. silent wrong answers (B1, B12) -- could ship;
2. crashes on plausible input (B3, B4) -- noticed immediately, fixed the same day;
3. policies and contracts (B2, B5, B7, B8) -- cause confusion for months;
4. structure (everything else) -- cause bugs later.

---

## Review checklist (the part you can reuse)

For code that scans, recurses, or reports "not found":

- [ ] Is every window/state/range that the problem asks about actually examined,
      or is the test in the wrong scope? (B1)
- [ ] Does each guard check exactly what its name and comment claim? (B1b)
- [ ] What does the function do with: `None`, an empty input, non-ASCII text,
      duplicate values, a value that is itself the "not found" marker? (B3, B7, B12)
- [ ] On failure, does it raise -- or does it print, or return a valid-looking
      value? (B2)
- [ ] Does the code have a stated input policy, and do all the functions in the
      file follow the same one? (B5, B7)
- [ ] Is the depth budget respected, or is the recursion one frame per element? (B4)
- [ ] Is the "no answer" value distinguishable from every possible answer? (B8, B12)
- [ ] Are there assignments nobody reads? (B9 -- and check with `ast`, not eyes)
- [ ] Is anything built with `s += piece` inside a loop? (B2c -- `"".join` or a
      slice instead)
- [ ] Does the same logic appear three times? (B11)
- [ ] Do the comments match the code that runs? (B14)
- [ ] Can the module be imported without side effects? (B15)
- [ ] Is there an oracle, and does every fast version get compared to it on
      *exhaustive* small inputs? (the whole chapter)

---

## Exercises

1. **Write the failing tests first.** Take B1 and write the three assertions that
   fail against the submission, then fix the code. How many of the eighteen
   entries can you reproduce *before* reading them?
2. **Find a nineteenth.** One difference between the two balanced programs is
   still uncatalogued: compare what each does with a string that *starts* with a
   non-letter, and with a string that ends with one. Write the model, the test
   and the catalogue entry.
3. **Make B12 come and go.** Construct an array of five elements containing
   `None` where `find_dominator_indices` is *right*, and one where it is wrong,
   and state the general rule.
4. **Attack your own oracle.** Add an optimisation to `reference` and see how
   many of the exhaustive tests it takes down. (Drop the `> self.length` short
   circuit in `is_balanced`, or re-introduce the `len(window) > tracker.length`
   guard, and watch `'abcabc'` fail.) Then break `pair_scan` on purpose and see
   which test file catches it first -- exhaustive, randomised, or the docs?
5. **Automate the taxonomy.** Write a checker (`tools/lint_architecture.py`?)
   that flags the classes that can be detected mechanically: dead stores (B9),
   module-level side effects (B15), `isalpha` used as an ASCII test (B3),
   functions returning both a value and a magic marker (B8, B12). Run it on the
   archive and see how many of the eighteen it finds.
6. **Measure the cost of not fixing B10.** Take the archived divide & conquer,
   fix only the index collection, and measure both versions on `n = 10^6` with a
   dominator present and absent. Report the ratio and compare it with the
   `O(n log n)` prediction.
