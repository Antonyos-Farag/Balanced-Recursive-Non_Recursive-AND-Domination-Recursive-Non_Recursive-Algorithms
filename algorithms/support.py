"""Small instrumentation helpers shared by the tools, the tests and the lab.

Two ideas live here:

``ReadCounter``
    A read-only sequence wrapper that counts **element reads**.  Wrap a string
    or a list in it and the algorithms under study will report, honestly, how
    many characters / items they looked at.  ``len()`` is free, ``s[i]`` costs
    one, ``s[i:j]`` costs ``j - i``, iterating costs one per element.  This is
    how ``docs/05-complexity-lab.md`` measures work instead of guessing.

``run_deep``
    Run a deeply recursive function in a worker thread that has a raised
    recursion limit *and* a large OS stack.  ``sys.setrecursionlimit`` alone is
    a trap: it makes CPython happy long after the C stack is gone, and the
    process dies with a segmentation fault instead of a ``RecursionError``.
    Raising both together is the safe way to keep a deep recursion alive.

Nothing in here is needed to use the algorithms; it is instrumentation, so it
lives apart from the algorithms themselves.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Sequence
from typing import Any, Callable, Iterable, List, Optional, Tuple

__all__ = [
    "ReadCounter",
    "format_int",
    "format_seconds",
    "run_deep",
    "timed",
    "Timing",
]


class ReadCounter(Sequence):
    """A sequence proxy that counts every element the caller looks at.

    Three counters are kept, and the split turns out to matter:

    ``point_reads``
        Single-element accesses (``s[i]``) and iterated elements.  This is
        *scan work*: the algorithm has to look at each element it examines.
    ``slice_reads``
        Characters copied by slicing (``s[i:j]`` counts ``j - i``).  This is
        *answer building*: work spent materialising a result, not searching.
    ``reads``
        The sum, for convenience.

    Why the split?  A scan that is linear can still be dominated by copying its
    answers: the pair scan in ``algorithms/balanced/fast.py`` examines O(n)
    positions on ``"ababab..."`` while copying Theta(n^2) characters' worth of
    improving answers.  Reporting one number would hide that; the benchmark in
    ``docs/05-complexity-lab.md`` shows both.

    >>> s = ReadCounter("abc")
    >>> s[0], s[1:3], list(s)
    ('a', 'bc', ['a', 'b', 'c'])
    >>> s.point_reads, s.slice_reads, s.reads
    (4, 2, 6)
    """

    __slots__ = ("_data", "point_reads", "slice_reads")

    def __init__(self, data: Sequence) -> None:
        self._data = data
        self.point_reads = 0
        self.slice_reads = 0

    # -- the accounting ---------------------------------------------------
    @property
    def reads(self) -> int:
        """Total element reads: ``point_reads + slice_reads``."""
        return self.point_reads + self.slice_reads

    def reset(self) -> None:
        """Set the counters back to zero (keeps the wrapped data)."""
        self.point_reads = 0
        self.slice_reads = 0

    @property
    def data(self) -> Sequence:
        """The wrapped sequence, un-instrumented."""
        return self._data

    # -- Sequence protocol ------------------------------------------------
    def __getitem__(self, index):  # type: ignore[override]
        if isinstance(index, slice):
            self.slice_reads += len(range(*index.indices(len(self._data))))
        else:
            self.point_reads += 1
        return self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        for item in self._data:
            self.point_reads += 1
            yield item

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ReadCounter({self._data!r}, reads={self.reads})"


class Timing:
    """The result of :func:`timed`: a duration plus what happened."""

    __slots__ = ("seconds", "result", "calls")

    def __init__(self, seconds: float, result: Any, calls: int) -> None:
        self.seconds = seconds
        self.result = result
        self.calls = calls

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Timing(seconds={self.seconds:.6g}, calls={self.calls})"


def timed(fn: Callable, *args, repeat: int = 1, **kwargs) -> Timing:
    """Call ``fn(*args, **kwargs)`` ``repeat`` times and keep the **best** time.

    Best-of-N is used rather than the mean because the mean is dominated by
    whatever else the machine was doing; the fastest run is the least noisy
    estimate of the work the code itself costs.
    """
    if repeat < 1:
        raise ValueError("repeat must be >= 1")
    best = None
    result = None
    for _ in range(repeat):
        started = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - started
        if best is None or elapsed < best:
            best = elapsed
    assert best is not None
    return Timing(best, result, repeat)


def run_deep(
    fn: Callable,
    *args,
    limit: int = 1_000_000,
    stack_mb: int = 512,
    **kwargs,
):
    """Run ``fn(*args, **kwargs)`` deep on the stack, in a worker thread.

    Raises whatever ``fn`` raises (including ``RecursionError`` if the limit is
    still too small).
    """
    box: List[Any] = []

    def worker() -> None:
        previous = sys.getrecursionlimit()
        sys.setrecursionlimit(limit)
        try:
            box.append(("ok", fn(*args, **kwargs)))
        except BaseException as exc:  # noqa: BLE001 - reported to the caller
            box.append(("err", exc))
        finally:
            sys.setrecursionlimit(previous)

    previous_stack = threading.stack_size()
    try:
        threading.stack_size(max(0, stack_mb) * 1024 * 1024)
        thread = threading.Thread(target=worker, name="run-deep")
        thread.start()
        thread.join()
    finally:
        threading.stack_size(previous_stack)

    if not box:  # pragma: no cover - defensive
        raise RuntimeError("worker thread produced no result")
    kind, payload = box[0]
    if kind == "err":
        raise payload
    return payload


# -- formatting -----------------------------------------------------------


def format_int(value: int) -> str:
    """``1234567`` -> ``'1,234,567'`` (grouped, so big numbers stay readable)."""
    return f"{value:,}"


def format_seconds(seconds: float) -> str:
    """Render a duration with a unit that suits its size."""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.0f} ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.1f} us"
    if seconds < 1.0:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds:.3f} s"


def format_ratio(value: float) -> str:
    """Render a speed-up ratio like ``12.4x``."""
    if value >= 100:
        return f"{value:.0f}x"
    if value >= 10:
        return f"{value:.1f}x"
    return f"{value:.2f}x"


def chain(*iterables: Iterable) -> Tuple[Any, ...]:  # pragma: no cover
    """Tiny helper kept for readability in the tools."""
    out: List[Any] = []
    for it in iterables:
        out.extend(it)
    return tuple(out)


def optional_int(text: Optional[str]) -> Optional[int]:  # pragma: no cover
    """Parse an optional CLI integer."""
    return None if text is None else int(text)
