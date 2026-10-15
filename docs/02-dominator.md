# 02 -- Dominators

> *An element is a **dominator** of a sequence when it occurs **strictly more
> than half** the time. Find it -- or report that there is none.*

Called the *majority element* in most textbooks and the *dominator* in the
exercise that inspired this repository (where the answer is a list of indices).
The two submitted programs both solve it; they disagree about almost everything
else, and their disagreements are more interesting than the algorithm.

---

## 1. Two facts that make the problem tractable

**Fact 1 -- the answer is unique.**
If `x` and `y` both occurred more than `n/2` times, they would together occur
more than `n` times. So the question is never *"which of several?"*; it is
*"which one, if any?"*. This is why the algorithm can carry a single candidate
around instead of a set, and why every implementation here can return one value
and be done.

**Fact 2 -- a candidate is cheap, a proof is not.**
There is a one-pass, O(1)-memory procedure that produces a value which *must* be
the dominator if a dominator exists (Boyer-Moore). It also produces a value when
no dominator exists, and that value is meaningless. Verification is therefore
mandatory, and it costs a second pass. Every bug in this corner of the
repository is a variation on forgetting Fact 2 or breaking Fact 1.

A third fact, used by one of the four implementations:

**Fact 3 -- in sorted order, the dominator sits in the middle.**
If `x` occurs more than `n/2` times, its copies form a block of length `> n/2` in
the sorted array, and that block must contain index `n // 2`. (If the block began
after `n // 2` it would need more than `n/2` slots to its right; if it ended
before `n // 2` it would need more than `n/2` slots to its left. Neither fits.)
So `sorted(a)[n // 2]` is the *only* possible dominator -- and must still be
counted.

## 2. The contract this repository uses

```python
Dominator(value=3, indices=(0, 2, 4, 6, 7))     # a real answer
None                                            # there is no dominator
```

One type, one absence marker, and the absence marker cannot be mistaken for an
answer because answers are objects. The archived programs between them use three
different encodings for "no dominator" (`-1`, `[]`, and an internal `None`
sentinel), and section 6 shows the price of the third one.

`Dominator` is a frozen dataclass, so it compares structurally, prints usefully,
and can be a dictionary key:

```python
>>> Dominator(3, (0, 2)) == Dominator(3, (0, 2))
True
>>> dominator.any_index([3, 1, 3, 2, 3, 4, 3, 3])   # "any index, or -1"
0
```

## 3. Boyer-Moore: cancel, elect, verify

The entire algorithm is five lines:

```python
candidate, count = None, 0
for value in a:
    if count == 0:            # nobody is standing: this value takes the seat
        candidate, count = value, 1
    elif value == candidate:  # a supporter joins
        count += 1
    else:                     # an opponent cancels one supporter
        count -= 1
```

**Invariant.** After processing `a[0..i]`, the pair `(candidate, count)` can be
described as: *"`count` copies of `candidate` survive from `a[0..i]`"*. Every
decrement annihilates one copy of the candidate against one element of a
different value, so no value that occurs more than half the time can be
annihilated completely: it would need more opponents than there are elements.

**Proof that the candidate is right when a dominator exists.**
Let `x` occur `m > n/2` times. Pair up every non-`x` element with a distinct
copy of `x`; there are fewer than `m` non-`x` elements, so at least one copy of
`x` is never paired and never cancelled. It is therefore either the final
candidate or was replaced by a candidate that... -- the standard proof prunes
this by induction on the array: pairs of different values can be *deleted* from
the array without changing which value dominates, and deleting a pair reduces
the length by 2 while removing at most one copy of `x`. Repeat until no pair of
different values remains: the array is then all one value, and it must be `x`.

**Why you cannot skip verification.** On `[1, 2, 3]` the vote ends with
candidate `3` and count `1`. Nothing about that is a majority. The trace, with
every step and the verification pass, is in `docs/traces/dominator-vote.txt`:

```
| i | a[i] | action  | candidate | count | survivors          |
| 0 | 3    | elect   | 3         |     1 | ######......       |
| 1 | 1    | cancel  | 3         |     0 | ............       |
| 2 | 3    | elect   | 3         |     1 | ######......       |
...
| 7 | 3    | support | 3         |     2 | ############       |
| - | -    | verify  | 3         |     5 | majority needs > 4 |
```

Note the last row: the vote's count is `2`, the *real* count is `5`. The vote's
counter measures surviving support, not occurrences, and the two numbers are
routinely different. Anyone who reads the count column as "how many times the
candidate occurred" has misunderstood the algorithm.

**Cost:** two passes, `O(n)` time, `O(1)` extra memory (plus the returned
indices). This is optimal for the problem, and it is what the submitted
non-recursive program implements -- correctly.

## 4. Divide & conquer: the halving lemma

**Lemma.** If `x` dominates `a[lo..hi]`, then `x` dominates at least one of the
halves `a[lo..mid]` and `a[mid+1..hi]`.

**Proof.** Suppose not. Then `x` occurs at most `floor(len1 / 2)` times in the
left half and at most `floor(len2 / 2)` times in the right half, so at most
`floor(len1/2) + floor(len2/2)` times in total. And for any integers,
`floor(p/2) + floor(q/2) <= floor((p+q)/2)`, so `x` occurs at most
`floor((len1+len2)/2)` times -- not more than half. Contradiction. ∎

The algorithm follows directly: ask each half for its dominator; if a half has
none, say so; if a candidate survives, count it over the whole range and keep it
only if it is really a majority.

```python
left  = majority_of_range(a, lo, mid)
right = majority_of_range(a, mid + 1, hi)
if left is not NOTHING and count(a, left, lo, hi) > size // 2:
    return left
if right is not NOTHING and count(a, right, lo, hi) > size // 2:
    return right
return NOTHING          # the lemma says this is safe
```

**Invariant.** The function returns the dominator of its range *if one exists*,
and `NOTHING` otherwise. Every value it hands back has been counted over the
range it claims to dominate. Compare that with Boyer-Moore, whose candidate is a
guess that the caller must verify: the divide & conquer pays for its strong
invariant with a second count at every level, which is exactly why it is slower.

The recursion tree for `[3, 1, 3, 2, 3, 4, 3, 3]` (`-` means "no dominator in
this range"), from `docs/traces/dominator-divide-tree.txt`:

```
`-- majority(lo=0, hi=7)  -> 3
    |-- majority(lo=0, hi=3)  -> '-'
    |   |-- majority(lo=0, hi=1)  -> '-'
    |   |   |-- majority(lo=0, hi=0)  -> 3
    |   |   `-- majority(lo=1, hi=1)  -> 1
    |   `-- majority(lo=2, hi=3)  -> '-'
    |       |-- majority(lo=2, hi=2)  -> 3
    |       `-- majority(lo=3, hi=3)  -> 2
    `-- majority(lo=4, hi=7)  -> 3
        |-- majority(lo=4, hi=5)  -> '-'
        |   |-- majority(lo=4, hi=4)  -> 3
        |   `-- majority(lo=5, hi=5)  -> 4
        `-- majority(lo=6, hi=7)  -> 3
            |-- majority(lo=6, hi=6)  -> 3
            `-- majority(lo=7, hi=7)  -> 3
```

Read the left half: `[3, 1]` has no dominator, `[3, 2]` has none, so `[3,1,3,2]`
has none -- and the recursion *knows* it without counting anything, because the
lemma says any dominator of the range would have to dominate a half. The right
half does better: `3` dominates both `[3, 4]`... no -- `[3, 4]` returns `-`, but
`3` is the candidate of `[3, 3]`, and then of `[3, 4, 3, 3]`, and finally of the
whole array. The value propagates up one level at a time, which is the recursion
doing its job.

**Cost.** `O(log n)` levels, and at each node at most two counts over that node's
range: `O(n log n)` element comparisons. Measured on `n = 100,000`
(`docs/traces/bench.txt`, which has both tables):

| input | positions read | time |
|---|---|---|
| `boyer_moore` | 200,000 | ~8.5 ms |
| `divide_and_conquer`, dominator present | 1,891,262 | ~103 ms |
| `divide_and_conquer`, no dominator present | 381,220 | ~49 ms |

(Timings are from the machine that generated `docs/traces/bench.txt`; the read
counts are exact and machine-independent.)

A dominator being present makes the recursion *slower*, not faster, which is
counter-intuitive until you look at where the counts happen: with no dominator
the counts fail early and the subtrees stop; with one, the candidate survives
deeper into the tree and every level above pays the full price of counting it.

The divide & conquer is therefore *not* the pragmatic choice. It is here because
the halving lemma is the cleanest statement of "what a majority has to do with
halves", because it parallelises trivially (the two recursive calls are
independent), and because comparing it with Boyer-Moore is a useful calibration:
the same answer, an order of magnitude apart, decided entirely by *how much
verification you do and where*.

## 5. The other two strategies

**`index_cache`** -- one pass, remembering every index of every value:

```python
seen = {}
for index in range(n):
    seen.setdefault(a[index], []).append(index)
for value, indices in seen.items():
    if len(indices) > n // 2:
        return Dominator(value, tuple(indices))
```

`O(n)` time and `O(n)` space, no second pass, no comparisons beyond hashing. On
these benchmarks it is the fastest of the four (~5 ms at `n = 100,000`, versus
~8.5 ms for Boyer-Moore and ~9.5 ms for sorting) because it reads each element
exactly once. Its price is
hashability: `[[1], [1], [2]]` has a dominator (`[1]`, twice) and `index_cache`
raises `TypeError`, while `boyer_moore` and `divide_and_conquer` answer it fine.

**`sort_and_pick_middle`** -- Fact 3, plus verification:

```python
candidate = sorted(a)[n // 2]
```

`O(n log n)` time, and it needs the values to be *comparable*: `[None, None, 1]`
raises `TypeError` inside `sorted`. Two of the four implementations therefore
have a precondition the other two do not, which is a perfectly good reason to
have more than one implementation of a simple problem -- as long as the
preconditions are written down. `tests/test_dominator_implementations.py` asserts
all three failure modes explicitly rather than letting them be folklore.

| function | time | space | needs | submits to |
|---|---|---|---|---|
| `boyer_moore` | `O(n)` | `O(1)` | nothing | any sequence |
| `index_cache` | `O(n)` | `O(n)` | hashable values | any sequence |
| `sort_and_pick_middle` | `O(n log n)` | `O(n)` | comparable values | any sequence |
| `divide_and_conquer` | `O(n log n)` | `O(log n)` stack | nothing | any sequence |

## 6. The sentinel problem (and the bug it caused)

The archived recursive program answers "no dominator" with an **empty list**,
and it uses **`None`** internally to mean "this range has no candidate":

```python
def find_dominator_recursive(A, left, right):
    if left == right:
        return (A[left], [left])
    ...
    return (None, [])            # "nothing found"
```

That is a collision, not a convention: `None` is a perfectly ordinary element of
a Python list, and the program cannot represent it.

```python
>>> find_dominator_indices([None, None, 1])    # None dominates: 2 of 3
[]
>>> find_dominator_indices([1, None, None])    # still a dominator: 2 of 3
[]
>>> find_dominator_indices([None, None])       # 2 of 2 -- and here it works!
[0, 1]
```

The third line is the one to stare at: the bug *comes and goes with the input
size*. A two-element array of `None`s accidentally works, because the base case
returns a value without ever consulting the sentinel. That is why this class of
bug survives testing by hand: whether it shows up depends on whether the sentinel
path is travelled at all.

The repaired version avoids the whole issue by never using a value as a marker:

```python
_NOTHING = object()        # a private, unique, non-value marker
...
if candidate is _NOTHING:  # `is`, not `==`: identity, not equality
    return None
```

**Design lesson, stated generally:** if "no answer" is expressed by a value that
could also be a real answer (`None`, `0`, `-1`, `""`, `[]`), the caller has to
know which values are special, and somebody will eventually pass one of them in.
A distinct type (`Dominator | None`), a private sentinel compared with `is`, or a
two-part return (`(found, value)`) all fix it. Three of those four patterns appear
in this package, and `tests/test_contracts.py` pins down exactly what each
archived program does with `[None, None, 1]`.

## 7. Every failure mode that actually happened

| # | defect | where | symptom |
|---|---|---|---|
| B8 | `-1` for "no dominator" | `dominator` | correct, but not composable with its sibling (`[]`) |
| B9 | `left_count = sum(...)` computed and never read | `find_dominator_recursive` | dead code, proven with `ast` in the tests |
| B10 | indices rebuilt at every level of the recursion | `find_dominator_recursive` | `O(n log n)` with a large constant instead of one pass at the top |
| B11 | three near-identical counting blocks | `find_dominator_recursive` | the same loop written three times; only one of the three can run |
| B12 | `None` as both marker and value | `find_dominator_recursive` | `[None, None, 1]` answers "no dominator" |
| B13 | redundant `if indices:` wrapper | `find_dominator_indices` | re-checks what the inner call already guarantees |
| B14 | comment promises `[0, 2, 4, 6, 7]`, program prints `[0]` | bottom of `dominator_recursive.py` | the printed output contradicts its own comment |

B9 has a static proof in the test suite:

```python
stores, loads = self._named_loads(legacy_dc, "left_count")
self.assertEqual(stores, 1)
self.assertEqual(loads, 0)      # assigned once, never read
```

which is a pleasant way to settle an argument: no reviewer gets to say "I think
that line is dead" without a counterexample to the test.

## 8. Exercises

1. **Patch the vote to survive missing verification.** Suppose a colleague
   deletes the verification pass "because it is `O(n)`". Construct three inputs
   of length 7 where the answer changes, and state the smallest `n` for which a
   wrong answer is possible at all.
2. **Prove Fact 3 carefully.** The correct statement must handle even and odd
   `n`, and must be about the *block* of copies in the sorted array.
3. **Make the divide & conquer cheaper.** The current version counts a candidate
   over the whole range as soon as it survives a half. There is a version that
   returns the left candidate if the halves agree (no count at all). Prove it
   correct, implement it, and count how many comparisons it saves on
   `[3, 1, 3, 2, 3, 4, 3, 3]`.
4. **Parallelise.** The two recursive calls in `majority_of_range` are
   independent. Sketch a version using `concurrent.futures` and predict the
   speed-up before measuring it. Why will it be less than 2x?
5. **Streaming dominator.** You are handed 10^9 integers one at a time and may
   not store them. Which of the four strategies survive? What can you *not*
   report without a second pass?
6. **Generalise to `n/k`.** For any `k`, at most `k-1` values can occur more than
   `n/k` times. Verify that the same cancellation idea generalises to finding
   *all* such values (the "Misra-Gries" summary), and say what it costs.
7. **Sentinel archaeology.** Find every place in the archived four files where a
   value doubles as a marker. For each, decide whether it can misfire, and write
   the input that demonstrates it.
8. **Which implementation would you ship?** Argue for one of the four using the
   measured numbers in `docs/traces/bench.txt`, then argue for a different one
   using preconditions and clarity.
