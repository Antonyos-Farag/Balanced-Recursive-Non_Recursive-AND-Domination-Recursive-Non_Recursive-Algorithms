"""Make the algorithms observable: call trees, vote walks, scan tables.

The functions that live here all follow the same idea: **do not read the code
and guess what it does — record what it does and print it.**  Each algorithm in
this repository accepts an optional ``trace`` hook, and this module contains the
recorders and the ASCII renderers that turn those hooks into something you can
read on a terminal.

Quick tour::

    >>> from algorithms import tracing
    >>> print(tracing.recursive_call_tree("aabbb", max_entries=200))  # doctest: +SKIP
    >>> print(tracing.vote_table([3, 1, 3, 2, 3, 4, 3, 3]))          # doctest: +SKIP
    >>> print(tracing.scan_table("aabbc"))                            # doctest: +SKIP

Nothing here is required for the algorithms to work; every hook defaults to
``None`` and the fast path stays fast.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "TraceLog",
    "render_table",
    "render_bar",
    "recursive_call_tree",
    "original_call_tree",
    "scan_table",
    "vote_table",
    "divide_conquer_tree",
    "pair_scan_table",
]


# ---------------------------------------------------------------------------
# the recorder
# ---------------------------------------------------------------------------


class _Node:
    __slots__ = ("name", "detail", "result", "children")

    def __init__(self, name: str, detail: Dict[str, Any]) -> None:
        self.name = name
        self.detail = detail
        self.result: Any = _MISSING
        self.children: List["_Node"] = []


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<no result>"

    def __bool__(self) -> bool:
        return False


_MISSING = _Missing()


def _format_value(value: Any) -> str:
    """Compact, deterministic rendering used inside trace lines."""
    if isinstance(value, str):
        text = repr(value)
    elif isinstance(value, bool) or value is None:
        text = repr(value)
    elif isinstance(value, (int, float)):
        text = repr(value)
    elif isinstance(value, (list, tuple)):
        text = "[" + ", ".join(_format_value(v) for v in value) + "]"
    elif isinstance(value, dict):
        text = "{" + ", ".join(f"{k}: {_format_value(v)}" for k, v in value.items()) + "}"
    else:
        text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


class TraceLog:
    """Records ``enter`` / ``exit`` / ``event`` calls and renders them as a tree.

    A ``TraceLog`` is deliberately dumb and cheap: it appends to a stack, it
    counts entries, and once ``max_entries`` is reached it keeps tracking depth
    (so the tree stays balanced) but stops storing nodes.  ``truncated`` then
    tells you that what you see is only a prefix of the run.
    """

    __slots__ = ("max_entries", "root", "_stack", "entries", "truncated", "flat_events")

    def __init__(self, max_entries: int = 4000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self.max_entries = max_entries
        self.root = _Node("<run>", {})
        self._stack: List[Optional[_Node]] = [self.root]
        self.entries = 0
        self.truncated = False
        self.flat_events: List[Dict[str, Any]] = []

    # -- recording --------------------------------------------------------
    def enter(self, name: str, **detail: Any) -> None:
        """Record entry into a call; pair it with :meth:`exit`."""
        if self.entries >= self.max_entries:
            self.truncated = True
            self._stack.append(None)
            return
        node = _Node(name, detail)
        parent = self._stack[-1]
        if parent is not None:
            parent.children.append(node)
        self._stack.append(node)
        self.entries += 1

    def exit(self, name: str, result: Any = _MISSING, **detail: Any) -> None:
        """Record leaving a call previously announced with :meth:`enter`."""
        if len(self._stack) <= 1:
            raise RuntimeError(f"exit({name!r}) without a matching enter(); log is unbalanced")
        node = self._stack.pop()
        if node is not None:
            if result is not _MISSING:
                node.result = result
            if detail:
                node.detail.update(detail)

    def event(self, kind: str, **detail: Any) -> None:
        """Record a leaf-level observation (a scan step, a count, a vote...)."""
        if self.entries < self.max_entries:
            self.flat_events.append({"kind": kind, **detail})
        else:
            self.truncated = True

    # -- reporting --------------------------------------------------------
    @property
    def depth(self) -> int:
        """Current stack depth (1 for the synthetic root)."""
        return len(self._stack)

    def __len__(self) -> int:
        return self.entries

    def __bool__(self) -> bool:
        return self.entries > 0

    def tree(self) -> str:
        """Render the recorded calls as an indented ASCII tree."""
        lines: List[str] = []
        self._render_node(self.root, "", True, lines, top=True)
        if self.truncated:
            lines.append(f"... trace truncated after {self.max_entries} entries")
        return "\n".join(lines)

    def _render_node(
        self,
        node: _Node,
        prefix: str,
        is_last: bool,
        lines: List[str],
        top: bool = False,
    ) -> None:
        if not top:
            connector = "`-- " if is_last else "|-- "
            detail = "".join(f", {key}={_format_value(val)}" for key, val in node.detail.items())
            result = "" if node.result is _MISSING else f"  -> {_format_value(node.result)}"
            lines.append(f"{prefix}{connector}{node.name}({detail.lstrip(', ')}){result}")
            prefix = prefix + ("    " if is_last else "|   ")
        for index, child in enumerate(node.children):
            self._render_node(child, prefix, index == len(node.children) - 1, lines)

    def events(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        """The flat ``event`` records, optionally filtered by ``kind``."""
        if kind is None:
            return list(self.flat_events)
        return [event for event in self.flat_events if event["kind"] == kind]


# ---------------------------------------------------------------------------
# generic ASCII tables
# ---------------------------------------------------------------------------


def render_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    *,
    align: Optional[Sequence[str]] = None,
    indent: str = "",
) -> str:
    """Render a plain ASCII table (no dependencies, no unicode box drawing).

    ``align`` is a per-column string of ``'<'`` (left) and ``'>'`` (right).
    """
    table = [[str(cell) for cell in row] for row in rows]
    widths = [len(str(headers[i])) for i in range(len(headers))]
    for row in table:
        if len(row) != len(headers):
            raise ValueError("row width does not match header width")
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    if align is None:
        align = ["<"] * len(headers)
    if len(align) != len(headers):
        raise ValueError("align width does not match header width")

    def line(left: str, mid: str, right: str, fill: str = "-") -> str:
        return indent + left + mid.join(fill * (width + 2) for width in widths) + right

    out = [line("+", "+", "+")]

    def cell(value: str, index: int) -> str:
        spec = align[index]
        return " " + format(value, spec + str(widths[index])) + " "

    out.append(indent + "|" + "|".join(cell(str(headers[i]), i) for i in range(len(headers))) + "|")
    out.append(line("+", "+", "+"))
    for row in table:
        out.append(indent + "|" + "|".join(cell(row[i], i) for i in range(len(headers))) + "|")
    out.append(line("+", "+", "+"))
    return "\n".join(out)


def render_bar(value: int, maximum: int, width: int = 20, fill: str = "#") -> str:
    """A tiny text bar chart, used for vote counts and frequency plots."""
    if maximum <= 0:
        return " " * width
    filled = int(round(width * value / maximum))
    filled = max(0, min(width, filled))
    return fill * filled + "." * (width - filled)


# ---------------------------------------------------------------------------
# balanced strings: watch the scans
# ---------------------------------------------------------------------------


def scan_table(s: str, *, max_rows: int = 200, casefold: bool = True) -> str:
    """Step-by-step table of the O(n^2) scan, straight from the trace hook."""
    from .balanced.iterative import brute_force

    log = TraceLog(max_entries=100_000)
    brute_force(s, casefold=casefold, trace=log)
    events = log.events("window")
    rows = []
    for event in events[:max_rows]:
        rows.append(
            (
                event["start"],
                event["end"],
                event["window"],
                event["counts"],
                event["distinct"],
                event["verdict"],
                event["best"],
            )
        )
    out = render_table(
        ["start", "end", "window seen", "counts", "distinct", "verdict", "best"],
        rows,
        align=[">", ">", "<", "<", ">", "<", ">"],
    )
    if len(events) > max_rows:
        out += f"\n({len(events) - max_rows} more rows not shown)"
    return out


def recursive_call_tree(
    s: str,
    *,
    max_entries: int = 4000,
    casefold: bool = True,
) -> str:
    """The call tree of the repaired recursive scan (TryEnd levels only)."""
    from .balanced.recursion import recursive

    log = TraceLog(max_entries=max_entries)
    recursive(s, casefold=casefold, trace=log)
    return log.tree()


def original_call_tree(s: str, *, max_entries: int = 4000) -> str:
    """The *archived* recursive program's call tree, patched at run time.

    The trick: ``TryStart`` and ``TryEnd`` are looked up in the module globals
    on every call, so replacing the module attributes with wrappers intercepts
    the recursion without touching a single line of the original code.  This is
    the honest way to show what the submission actually did.
    """
    from .original import balanced_recursive as legacy

    log = TraceLog(max_entries=max_entries)
    saved = (legacy.TryStart, legacy.TryEnd)

    def trace_start(fn):
        # TryStart(S, n, start, longest, best_list)
        def wrapper(*args, **kwargs):
            log.enter("TryStart", start=args[2], longest=args[3])
            result = fn(*args, **kwargs)
            log.exit("TryStart", result=result)
            return result

        return wrapper

    def trace_end(fn):
        # TryEnd(S, n, start, end, freq, distinct, longest, best_list)
        def wrapper(*args, **kwargs):
            log.enter(
                "TryEnd",
                start=args[2],
                end=args[3],
                freq="[" + ", ".join(str(f) for f in args[4] if f) + "]",
                distinct=args[5],
            )
            result = fn(*args, **kwargs)
            log.exit("TryEnd", result=result)
            return result

        return wrapper

    try:
        legacy.TryStart = trace_start(saved[0])
        legacy.TryEnd = trace_end(saved[1])
        legacy.LBS(s)
    finally:
        legacy.TryStart, legacy.TryEnd = saved
    return log.tree()


# ---------------------------------------------------------------------------
# dominator: watch the vote and the tree
# ---------------------------------------------------------------------------


def vote_table(a: Sequence[Any], *, show_bar: bool = True) -> str:
    """Table of every Boyer-Moore step: what was seen, and what was kept."""
    from .dominator.vote import walk_votes

    steps = walk_votes(a)
    if not steps:
        return "(empty array: nothing to vote on)"
    longest = max(step.count for step in steps)
    rows = []
    for step in steps:
        bar = render_bar(step.count, max(longest, 1), width=12) if show_bar else ""
        rows.append(
            (
                step.index,
                _format_value(step.value),
                step.action,
                _format_value(step.candidate),
                step.count,
                bar,
            )
        )
    last = steps[-1]
    rows.append(
        (
            "-",
            "-",
            "verify",
            _format_value(last.candidate),
            last.final_count,
            f"majority needs > {last.size // 2}",
        )
    )
    return render_table(
        ["i", "a[i]", "action", "candidate", "count", "survivors"],
        rows,
        align=["<", "<", "<", "<", ">", "<"],
    )


def divide_conquer_tree(a: Sequence[Any], *, max_entries: int = 4000) -> str:
    """The divide & conquer recursion tree, showing candidate and counts."""
    from .dominator.divide import divide_and_conquer

    log = TraceLog(max_entries=max_entries)
    divide_and_conquer(a, trace=log)
    return log.tree()


# ---------------------------------------------------------------------------
# balanced strings: the pair-scan (fast) algorithm
# ---------------------------------------------------------------------------


def pair_scan_table(s: str, *, casefold: bool = True) -> str:
    """Per-letter-pair report for the fast algorithm: blocks, best, verdict."""
    from .balanced import core
    from .balanced.fast import pair_scan_report

    text = core.normalize(s, casefold=casefold)
    report = pair_scan_report(text)
    rows = []
    for row in report:
        rows.append(
            (
                row.pair,
                row.blocks,
                row.block_sizes,
                row.best_length,
                row.substrings or "-",
            )
        )
    out = render_table(
        ["pair", "blocks", "block sizes", "best", "substrings found"],
        rows,
        align=["<", ">", "<", ">", "<"],
    )
    best = max((row.best_length for row in report), default=0)
    out += f"\nbest over all pairs: {best}"
    return out
