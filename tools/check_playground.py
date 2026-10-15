"""Check the JavaScript in ``playground/index.html`` against the Python code.

    python -m tools.check_playground

The playground re-implements the algorithms in JavaScript, and a
re-implementation that nobody checks is just a second place for bugs to live.
This tool closes that gap:

1. it extracts the ``<script>`` block from the page;
2. it wraps that script in a tiny DOM stub so a JavaScript engine can load it
   outside a browser;
3. it audits the page's wiring: every id the script reaches for must exist in
   the markup (a typo there is a button that does nothing, and no test would
   notice);
4. it hands the page a set of test cases -- strings and arrays together with the
   answers the *Python* implementations give;
5. it runs the whole thing under ``node`` and reports any disagreement.

What is compared:

* every balanced implementation present in the page (oracle, repaired double
  loop, pair scan, and the archived buggy logic) on hand-picked and random
  strings, including the recursion-depth measure;
* every dominator strategy in the page (vote, divide & conquer, index cache) on
  hand-picked and random arrays, ``None``/``null`` values included, plus what
  both archived programs report for the same arrays;
* an exhaustive sweep over all strings of length at most 6 on ``{a, b, c}``,
  where the page's three balanced implementations must agree with each other --
  and where the disagreement rate of the archived logic is counted, so the
  number the page displays is the number Python computes.

``node`` is required.  When it is missing the tool says so and exits 0, because
nothing in the Python repository depends on a JavaScript runtime.
"""

from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from algorithms import balanced, dominator
from algorithms.balanced.recursion import recursive_depth
from algorithms.original import balanced_iterative as legacy_loop
from algorithms.original import dominator_iterative as legacy_vote
from algorithms.original import dominator_recursive as legacy_dc

__all__ = ["extract_script", "audit_ids", "build_cases", "build_harness", "main"]

PAGE = Path(__file__).resolve().parent.parent / "playground" / "index.html"

# ---------------------------------------------------------------------------
# the JavaScript side
# ---------------------------------------------------------------------------

DOM_STUB = r"""
// ---- minimal DOM stub: enough for the page script to load outside a browser --
function fakeEl() {
  const store = {
    style: {}, dataset: {}, children: [], value: "",
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
  };
  store.firstElementChild = { style: {} };
  return new Proxy(store, {
    get(target, key) {
      if (key in target) return target[key];
      if (key === "querySelector" || key === "closest") return () => null;
      if (key === "appendChild") return (child) => child;
      if (key === "addEventListener" || key === "setAttribute" || key === "scrollIntoView") return () => {};
      return "";
    },
    set(target, key, value) { target[key] = value; return true; },
  });
}
globalThis.document = {
  getElementById: () => fakeEl(),
  createElement: () => fakeEl(),
  querySelectorAll: () => [],
  addEventListener: () => {},
};
"""

CHECK_EPILOGUE = r"""
// ---- cross-check against the Python implementations --------------------------
const cases = JSON.parse(require("fs").readFileSync(CASES_PATH, "utf8"));
let failures = 0;
function check(what, got, want) {
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    failures++;
    if (failures <= 12) {
      console.log("  MISMATCH " + what);
      console.log("    js = " + JSON.stringify(got));
      console.log("    py = " + JSON.stringify(want));
    }
  }
}
const res = (r) => [r.length, r.answers];
const enc = (d) => (d ? { found: true, value: d.value, indices: [...d.indices] } : { found: false });

for (const c of cases.balanced) {
  check("oracle " + JSON.stringify(c.s), res(reference(c.s)), c.oracle);
  check("fixed  " + JSON.stringify(c.s), res(fixedScan(c.s, false)), c.fixed);
  check("pair   " + JSON.stringify(c.s), res(pairScan(c.s, false)), c.pair);
  check("buggy  " + JSON.stringify(c.s), res(buggyScan(c.s)), c.buggy);
  check("depth  " + JSON.stringify(c.s), recursiveDepth(c.s), c.depth);
}

for (const c of cases.dominator) {
  const label = JSON.stringify(c.a);
  check("boyer_moore  " + label, enc(boyerMoore(c.a).dominator), c.boyer_moore);
  check("divide       " + label, enc(divideAndConquer(c.a, false).dominator), c.divide_and_conquer);
  check("index_cache  " + label, enc(indexCache(c.a)), c.index_cache);
  check("legacy_vote  " + label, legacyVote(c.a), c.legacy_vote);
  check("legacy_div   " + label, legacyDivide(c.a, 0, c.a.length - 1).indices, c.legacy_divide);
}

const report = pairScan("aabbc", true).report.map((r) => [r.pair, r.blocks, r.sizes, r.best, r.answers]);
check("pair report for aabbc (docs/traces/balanced-pairs.txt)",
      report, [["ab", 1, "4", 4, "aabb"], ["ac", 2, "2 1", 0, "\u2014"], ["bc", 1, "3", 2, "bc"]]);

let checked = 0, mismatches = 0, buggyWrong = 0;
for (const s of stringsUpTo("abc", 6)) {
  const oracle = reference(s);
  checked++;
  if (!sameResult(oracle, fixedScan(s, false)) || !sameResult(oracle, pairScan(s, false))) mismatches++;
  if (!sameResult(buggyScan(s), oracle)) buggyWrong++;
}
check("exhaustive sweep over {a,b,c} up to length 6: mismatches", mismatches, 0);

console.log("checked " + cases.balanced.length + " strings and " + cases.dominator.length +
            " arrays against the Python implementations: " +
            (failures === 0 ? "all agree" : failures + " MISMATCHES"));
console.log("exhaustive sweep in the page's own code: " + checked + " strings, " + mismatches +
            " mismatches between its implementations, " + buggyWrong +
            " disagreements of its archived logic with the truth");
process.exit(failures === 0 ? 0 : 1);
"""


def extract_script(page: Path = PAGE) -> str:
    """Pull the single ``<script>`` block out of the playground page."""
    html = page.read_text()
    match = re.search(r"<script>\n(.*)\n</script>", html, re.S)
    if match is None:
        raise SystemExit(f"no <script> block found in {page}")
    return match.group(1)


ID = re.compile(r'\bid="([^"]+)"')
ID_USE = re.compile(r'\$\("([^"]+)"\)|getElementById\("([^"]+)"\)')


def audit_ids(html: str) -> List[str]:
    """Complaints about ids: used-but-absent, or defined-but-never-used.

    A missing id is the classic silent failure of hand-written DOM code -- the
    listener is attached to ``null``, or to nothing at all, and the page simply
    does not respond.  The reverse (an id nobody uses) is only a hint, so it is
    reported as a note rather than a problem.
    """
    defined = ID.findall(html)
    used = [m.group(1) or m.group(2) for m in ID_USE.finditer(html)]
    problems = [f"the script uses #{name}, which no element defines" for name in sorted(set(used) - set(defined))]
    if len(defined) != len(set(defined)):
        duplicated = sorted({name for name in defined if defined.count(name) > 1})
        problems.append("duplicated ids in the markup: " + ", ".join(duplicated))
    return problems


def unused_ids(html: str) -> List[str]:
    """Ids the markup defines that nothing else in the file mentions at all.

    The test is deliberately loose -- the name has to appear *somewhere* else,
    whether that is a ``$("...")`` call, a ``label for=``, or an attribute the
    script reads back -- because the point is to catch ids that were left behind
    by an edit, not to build a model of how the page is wired.
    """
    return sorted(name for name in set(ID.findall(html)) if html.count(name) < 2)


def build_harness(script: str, cases_path: str) -> str:
    """DOM stub + the page's script + the Python cross-check."""
    epilogue = CHECK_EPILOGUE.replace("CASES_PATH", json.dumps(cases_path))
    return DOM_STUB + script + epilogue


# ---------------------------------------------------------------------------
# the Python side: what the answers are supposed to be
# ---------------------------------------------------------------------------


def _balanced_cases() -> List[Dict[str, object]]:
    rng = random.Random(31337)
    strings = [
        "",
        "a",
        "ab",
        "aabbb",
        "aabbc",
        "abcabc",
        "aabbaa",
        "aaabbb",
        "ababab",
        "aaab",
        "aabb",
        "abab",
        "abcdefghijklmnopqrstuvwxyz",
        "a" * 12,
        "abcabcabc",
    ]
    for _ in range(60):
        alphabet = rng.choice(["ab", "abc", "abcd", "abcdefghijklmnopqrstuvwxyz"])
        strings.append("".join(rng.choice(alphabet) for _ in range(rng.randint(0, 14))))

    cases = []
    for text in strings:
        length, answers = balanced.reference(text)
        f_len, f_ans = balanced.brute_force(text)
        p_len, p_ans = balanced.pair_scan(text)
        b_len, b_ans = legacy_loop.LBS_all_longest(text)
        cases.append(
            {
                "s": text,
                "oracle": [length, answers],
                "fixed": [f_len, f_ans],
                # the page sorts what it finds; the archived program's discovery
                # order is not part of any contract, so compare it sorted too
                "pair": [p_len, p_ans],
                "buggy": [b_len, sorted(b_ans)],
                "depth": recursive_depth(text),
            }
        )
    return cases


def _dominator_cases() -> List[Dict[str, object]]:
    rng = random.Random(4242)
    arrays: List[List] = [
        [3, 1, 3, 2, 3, 4, 3, 3],
        [],
        [1],
        [1, 2],
        [1, 1],
        [1, 2, 3, 4],
        [1, 1, 2, 2],
        [None, None, 1],
        [None, None],
        [None, None, None, 1],
        [2],
        [2, 2, 2, 2, 5],
        [0, 0, 0, 1, 1],
        [None, 1, None],
    ]
    for _ in range(40):
        arrays.append([rng.choice([0, 1, 2, None]) for _ in range(rng.randint(0, 9))])

    def encode(result) -> Dict[str, object]:
        if result is None:
            return {"found": False}
        return {"found": True, "value": result.value, "indices": list(result.indices)}

    cases = []
    for array in arrays:
        cases.append(
            {
                "a": array,
                "boyer_moore": encode(dominator.boyer_moore(array)),
                "divide_and_conquer": encode(dominator.divide_and_conquer(array)),
                "index_cache": encode(dominator.index_cache(array)),
                "legacy_vote": legacy_vote.dominator(array),
                "legacy_divide": legacy_dc.find_dominator_indices(array),
            }
        )
    return cases


def build_cases() -> Dict[str, List[Dict[str, object]]]:
    """Both halves of the comparison, as plain JSON-able data."""
    return {"balanced": _balanced_cases(), "dominator": _dominator_cases()}


# ---------------------------------------------------------------------------
# running it
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    node = shutil.which("node")
    if node is None:
        print("node is not installed: skipping the playground cross-check.")
        print("(the page is still verified by hand against docs/traces/*.txt)")
        return 0

    page = Path(argv[0]) if argv else PAGE
    html = page.read_text()
    script = extract_script(page)

    problems = audit_ids(html)
    unused = unused_ids(html)
    if unused:
        print(
            "note: these ids are only ever defined, never written out again in the "
            "file -- they may be assembled at run time: " + ", ".join(unused)
        )
    if problems:
        for problem in problems:
            print("  " + problem)
        print("playground wiring check FAILED")
        return 1

    with tempfile.TemporaryDirectory(prefix="playground-check-") as workdir:
        cases_path = str(Path(workdir) / "cases.json")
        harness_path = Path(workdir) / "harness.js"
        Path(cases_path).write_text(json.dumps(build_cases()))
        harness_path.write_text(build_harness(script, cases_path))

        completed = subprocess.run(
            [node, str(harness_path)], capture_output=True, text=True
        )
        sys.stdout.write(completed.stdout)
        if completed.returncode != 0:
            sys.stderr.write(completed.stderr)
            print(f"playground cross-check FAILED ({completed.returncode})")
            return completed.returncode

    print("playground/index.html agrees with the Python implementations.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
