# 03 -- Recursion and iteration are the same algorithm, twice

The assignment asked for the balanced-substring program twice: once with loops,
once with recursion. It is a common assignment because it feels like it teaches
the difference between the two styles. It does not, quite -- what it teaches is
that **there is no difference in what can be computed, only in where the state
lives**.

This chapter does the translation in both directions, on the assignment's own
code, and measures what the choice actually costs.

---

## 1. The only thing that differs: where the state lives

Any loop and any recursion carry the same four things:

| what the computation needs | loop | recursion |
|---|---|---|
| where am I? | loop variable, mutated | an argument, private to each level |
| what have I accumulated? | a local, mutated | an argument, copied or shared |
| what is the result so far? | a local, mutated | an argument, threaded up or shared |
| what is left to do? | the remaining iterations | the call stack |

Recursion is not "more mathematical"; it is a program that stores its pending
work on the call stack and its position in arguments. A loop stores the same
information in variables and relies on the interpreter to re-run the body. When
you see the correspondence, translations stop being a matter of taste:

* **tail recursion** (the recursive call is the *last* thing the function does,
  with nothing to do afterwards) becomes a loop, directly;
* **structural recursion** (the recursive call is followed by work, or the
  shape of the recursion mirrors the data) becomes a loop *plus an explicit
  stack* -- or, when the state is simple enough, just a loop.

## 2. Translation one: tail recursion → loop

The submitted `TryStart` is textbook tail recursion:

```python
def TryStart(S, n, start, longest, best_list):
    if start == n:
        return longest, best_list
    freq = [0] * 26
    distinct = 0
    longest, best_list = TryEnd(S, n, start, start, freq, distinct, longest, best_list)
    return TryStart(S, n, start + 1, longest, best_list)     # <- last thing it does
```

Nothing happens between the call and the return, so the caller's frame is pure
overhead: its entire state is `(start, longest, best_list)`. Rewrite as a loop:

```python
for start in range(n):
    freq = [0] * 26
    distinct = 0
    longest, best_list = TryEnd(S, n, start, start, freq, distinct, longest, best_list)
return longest, best_list
```

That is the whole translation, and it is *exact*: same computation, same
`O(n)` calls, one frame instead of two per iteration.

**Python will not do this for you.** CPython has no tail-call optimisation (by
design -- the traceback stays honest), so `TryStart` costs a real frame for every
starting position. On a 10,000-character string the recursion would need 10,000
frames, and it dies at 997 -- the largest input that survives is 996 characters.
The repository's repaired recursion therefore
uses the loop form for `start`, and keeps the recursion for the part that is
genuinely recursive:

```python
def recursive_normalized(text, *, trace=None):
    tracker = BestTracker()
    for start in range(len(text)):
        _try_end(text, start, start, [0] * 26, 0, tracker, trace)   # recursion stays
    return tracker.result()
```

**How to tell whether Python is the right tool at all:** if the recursion is
*only* tail recursion, write a loop. This is not a style preference -- it is the
difference between a function that works for any input and one that raises
`RecursionError` at 997 (996 succeeds).

## 3. Translation two: the inner recursion → the inner loop

`TryEnd` is not tail recursion, because each level does work before recursing
(fold one character into the window) and its frames carry state:
`(start, end, freq, distinct)`.

The mechanical translation is a loop with the state that used to be arguments:

```python
def round_trip(text):                    # from algorithms/balanced/iterative.py
    tracker = BestTracker()
    for start in range(len(text)):       # <- TryStart, unrolled
        freq = [0] * 26                  #    TryStart's fresh table per start
        distinct = 0
        for end in range(start, len(text)):     # <- TryEnd, unrolled
            index = ord(text[end]) - ord("a")   #    fold text[end] into freq
            if freq[index] == 0:
                distinct += 1
            freq[index] += 1

            if distinct > 2:
                break                     #    TryEnd's "if distinct > 2: return"

            if distinct == 2 and equal_pair(freq):
                tracker.consider_span(text, start, end)

            # TryEnd recursed with end + 1; `for end in range(...)` does it
    return tracker.result()
```

Compare that with `brute_force`, which was written as a loop from the start. They
are the same function:

```python
>>> from algorithms import balanced
>>> balanced.round_trip("aabbb") == balanced.brute_force("aabbb")
True
```

**Two programs that share nothing but the problem statement collapse into one.**
That is the practical value of doing the translation: it is the fastest way to
find out whether two implementations really are the same algorithm, or only
look similar.

### Why is the explicit stack missing?

The recipe says "loop plus an explicit stack", but the translation above has no
stack. It does not need one, and the reason is worth stating precisely:

> The recursion is **chain-shaped**: every call has at most one recursive call,
> and it is the *last* thing that happens. A DFS over a chain visits one state at
> a time, so the stack never holds more than one pending item -- and a stack of
> size one is a variable.

Written out, the explicit-stack version makes this visible:

```python
stack = [(start, [0] * 26, 0)]          # (end, freq, distinct)
while stack:
    end, freq, distinct = stack.pop()
    ...do the work for this state...
    if distinct <= 2 and end + 1 <= n:
        stack.append((end + 1, freq[:], distinct))   # exactly one push
```

At every iteration the stack is `[...one item...]`. The `pop`/`append` pair is
the loop variable `end`, and the loop is the translation. (If you add a check for
"third letter", the single push becomes conditional -- which is the `break`.)

Explicit stacks earn their keep when the recursion **branches**: two or more
recursive calls, a backtracking search, a graph traversal with several pending
neighbours. That is precisely the shape of the dominator's divide & conquer
([`docs/02`](02-dominator.md)), which is where this repository *does* keep the
recursion and *does* pay for it in frames -- `O(log n)` of them, which is why it
is fine.

## 4. The state you thread vs the state you share

Both submissions thread their accumulator through the argument list:

```python
def TryEnd(S, n, start, end, freq, distinct, longest, best_list):
    ...
    return TryEnd(S, n, start, end + 1, freq[:], distinct, longest, best_list)
```

Eight parameters, two of which (`longest`, `best_list`) are returned unchanged by
almost every call and used by almost none of them. The recursion manages to look
complicated because it is passing a shared notepad around between every frame.

The repaired versions use one accumulator object:

```python
tracker = BestTracker()               # length + the set of answers at that length
for start in range(len(text)):
    _try_end(text, start, start, [0] * 26, 0, tracker, trace)
return tracker.result()
```

`_try_end` still receives `freq` and `distinct` as arguments -- they are
genuinely *per window* state, and each level needs its own -- but the answer no
longer travels. It makes the recursion smaller, the trace readable (every frame
returns the same pair, which the original tree in
`docs/traces/balanced-original-tree.txt` shows at length), and it makes the
translation to a loop mechanical, because the loop already had a variable waiting
for it.

**Rule of thumb.** Thread state that differs per level; share state that is a
property of the whole search. If you are returning the shared state up the call
chain, you have already given it a home somewhere else.

## 5. `freq[:]`: two ways to give each level its own copy

The submissions copy the frequency table at the call site:

```python
return TryEnd(S, n, start, end + 1, freq[:], distinct, longest, best_list)
```

Each level then owns a private copy and mutates it freely; nothing needs
undone, because the copy is thrown away when the frame returns. 26 integers per
call, at every level, for every start.

The alternative is the classic backtracking pattern: one table, mutated going
down, un-mutated coming back up.

```python
def _walk(text, start, end, freq, distinct, tracker):
    index = ord(text[end]) - ord("a")
    is_new = freq[index] == 0
    freq[index] += 1
    if is_new and distinct == 2:
        freq[index] -= 1                    # undo, then give up on longer windows
        return
    if is_new:
        distinct += 1
    if distinct == 2 and equal_pair(freq):
        tracker.consider_span(text, start, end)

    _walk(text, start, end + 1, freq, distinct, tracker)

    freq[index] -= 1                        # undo: the caller's table is intact
```

Both are correct (`tests/test_balanced_implementations.py` checks
`recursive_shared_freq` against the oracle on every short string). The measured
difference, on `"ab" * 250`:

| implementation | positions read | slices copied | best of 3 |
|---|---|---|---|
| `recursive` (copy per level) | 125,250 | 62,750 | 138.7 ms |
| `recursive_shared_freq` (mutate and undo) | 125,250 | 62,750 | 101.5 ms |
| `brute_force` (plain loop) | 125,250 | 62,750 | 77.2 ms |

Three observations:

1. **The copies are invisible to a character-counting metric** -- both read the
   same characters. A metric that copies 26 integers per call changes the *time*,
   not the read count; this is exactly why the repository reports both.
2. **Mutate-and-undo is ~10% faster here**, not 10x. `freq[:]` on a 26-element
   list is a fast `memcpy`, and the recursion's real cost is the interpreter
   overhead per frame.
3. **The loop form is ~1.8x faster than either recursion.** That is the honest
   price of recursive style in CPython: an interpreted frame per level.

The pattern still matters when the state is big: copy a 26-int list and nobody
notices; copy a 10,000-element `visited` array per level and the program collapses.
Learn the undo pattern for the cases where it pays, not because it is always
faster.

## 6. Depth: the constraint nobody writes down

Every recursion has a depth budget. For this one it is one frame per character of
the window being scanned, plus a terminating frame, and the budget is CPython's
default recursion limit of 1000.

| implementation | longest input that survives |
|---|---|
| archived `LBS` (`TryStart` + `TryEnd`, one frame each per position) | 996 characters |
| repaired `recursive` (loop for `start`, recursion for the window) | 996 characters |
| `recursive_shared_freq` | 996 characters |
| `brute_force`, `round_trip`, `pair_scan` (no recursion) | no depth limit at all; only time limits them (2,000 characters in `tests/test_recursion.py`, more in `tools/bench.py`) |

The two recursions land within one character of each other, which is the point:
**the depth belongs to the algorithm, not to the bug.** Fixing the misplaced
balance test bought exactly zero extra capacity.

`tests/test_recursion.py` measures the depth profile directly:

```python
>>> recursive_depth("ab" * 10)      # never a third letter: scans run to the end
21                                  # = 20 characters of window + 1 terminating frame
>>> recursive_depth("abcabc")       # every scan dies at the third letter
3
```

### A frame per level is a design decision

While this repository was being written, the trace hook for `_try_end` was
implemented as two functions -- a wrapper that logged entry/exit and a body that
did the work:

```python
def _try_end(...):
    trace.enter("TryEnd", ...)
    _scan_step(...)            # <- one extra frame per character
    trace.exit("TryEnd", ...)
```

It worked, and it halved the usable string length: the measured wall moved from
996 characters to about **497**. The fix was to write the body with a single exit
point so the logging needs no extra call, and the wall returned to 996.

That is not a historical anecdote -- the wrapper approach is still in the
repository, as `tracing.original_call_tree`, which traces the *archived* program
by replacing `TryStart`/`TryEnd` with logging wrappers. Measured today, it
survives 495 characters of `"a" * n` where the untraced program survives 996.
The repaired `recursive()` takes a `trace=` argument instead, so tracing it costs
zero frames.

The lesson generalises further than one helper function: in CPython **the number
of frames per level is part of your capacity**, and adding a decorator, a
`try/finally` wrapper or a "small helper" to a deep recursion is a capacity
decision, not a refactoring detail. `tests/test_recursion.py` now asserts the
profile (`recursive_depth("ab" * 300) == 601`) so that a future edit that costs a
frame is caught by a test rather than by a user.

### When you must go deeper

Three legitimate answers, in increasing order of desperation:

1. **Rewrite the tail recursion as a loop.** Free, exact, and it is what this
   repository does for `start`.
2. **Keep the recursion, raise both limits.** `sys.setrecursionlimit` alone is a
   trap: CPython will happily accept a limit that the C stack cannot support, and
   the process dies with a segmentation fault instead of a `RecursionError`.
   `algorithms.support.run_deep` raises the limit *and* runs the function in a
   thread with a large stack:

   ```python
   >>> from algorithms.support import run_deep
   >>> from algorithms import balanced
   >>> run_deep(balanced.recursive, "aabbb" * 300)[0]     # 1,500 characters
   12
   ```

   This is a tool, not a design: a thread with a 512 MB stack is a large hammer.
3. **Use an explicit stack.** Always available, never limited by the interpreter,
   and (for branching searches) often clearer than the recursion. It costs you
   the ability to write the recursion recursively, which for a chain-shaped
   search -- as section 3 shows -- means it costs nothing at all.

## 7. Things that do *not* transfer from the loop version

A short list of Python-specific traps, each of which appears in this repository's
*first* drafts:

* **`lru_cache` will not help you.** Memoisation pays when subproblems repeat.
  Here the "subproblem" is `(start, end, freq, distinct)`, and the frequency table
  is different for every window: there is nothing to cache. Worse, caching a
  function whose accumulator mutates would return stale answers -- the classic
  "the cache made it wrong" bug. The recursion here has no overlapping
  subproblems, and that is why it is `O(n^2)` calls rather than exponential: the
  call *tree* has `O(n^2)` nodes, and every one of them is distinct work.
* **Default arguments are shared.** A signature like
  `def scan(text, freq=[0] * 26)` would give every top-level call the same table
  and produce answers that depend on the previous call. The repository passes
  fresh tables explicitly, and `tests/test_balanced_implementations.py` calls each
  implementation repeatedly to catch exactly this kind of state leak.
* **Mutating a parameter is fine *if* every level owns its copy.** Both
  recursive styles here mutate `freq`; one owns a private copy, the other undoes
  its mutation. Mutating a parameter that the caller still holds -- `distinct` in
  a version that passes the same `freq` without undo -- produces answers that
  depend on evaluation order.
* **Exceptions and deep stacks interact badly.** A `RecursionError` raised 900
  frames down is hard to read; `traceback.print_stack()` prints hundreds of
  identical frames. When a recursion fails deep inside, the useful information is
  the *depth profile* (`recursive_depth`) and the input size, not the traceback.
* **Recursion in a `__del__`, a generator, or a comprehension** adds hidden
  frames. None of them appear here, and that is deliberate.

## 8. A translation recipe

When you have to move between the two styles, in either direction:

1. **Write down the four states** (position, accumulated state, result so far,
   pending work) for the version you have.
2. **If the recursive call is the last statement**, replace it with a loop
   assignment: the parameters of the call become the loop variables. No stack
   needed.
3. **If the state is per level**, pass it as an argument -- or keep one copy and
   *undo* the mutation on the way back. Decide which, and write down why.
4. **If the state is global to the search**, put it in one object that both
   versions can hold. Then the translations are mechanical, and the two versions
   stay comparable.
5. **Check the depth budget**: frames per level x maximum nesting. If it exceeds
   a few hundred, step 2 is mandatory.
6. **Check that the two versions agree** on every input you can enumerate --
   which, for this repository, means the exhaustive tests in
   `tests/test_balanced_implementations.py` rather than a handful of examples.

## 9. Exercises

1. **Translate §3's `round_trip` back into recursion** line by line, without
   looking at `recursion.py`, then diff your version against it. Where do they
   differ, and does it matter?
2. **Build the branching counterexample.** Write a short recursive function that
   branches (for example, counting balanced substrings rather than finding the
   longest) and translate it to an explicit stack. Where does the stack grow
   beyond one entry, and by how much?
3. **Measure the price of a decorator.** Write a `@logged` decorator that
   records call counts, apply it to `_try_end`, and measure the new recursion
   wall. Predict it first.
4. **Break the depth measurement.** Find an input where `recursive_depth` is much
   larger than `len(text)` -- is that possible here? Why not?
5. **Fix the copy without the undo.** Rewrite `recursive` to copy `freq` lazily
   (only when the next level will mutate it). Does it get faster? Does it stay
   correct? (Careful: this one is a trap, and the trap is instructive.)
6. **Make the recursion survive 100,000 characters** without `run_deep` and
   without changing the answer: turn both recursions into loops. How does your
   `round_trip` differ from the existing one? Then measure it against
   `pair_scan`.
7. **Find the limit empirically.** Write a function that finds the largest `n`
   for which `recursive("a" * n)` succeeds, and explain why it differs from the
   recursion limit by the number it differs by. (Hint: count the frames between
   `unittest` and `_try_end`.)
