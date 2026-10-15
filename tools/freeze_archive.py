"""Record SHA-256 digests of the four archived submissions.

    python -m tools.freeze_archive            # write algorithms/original/FROZEN.sha256
    python -m tools.freeze_archive --check    # verify without writing

The archive is evidence.  ``tests/test_original_characterization.py`` recomputes
these digests, so any edit to ``algorithms/original/*.py`` fails the suite.  That
is the intended behaviour: when the code under study changes, the bug reports,
the traces and the benchmarks all become statements about a file that no longer
exists.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
from typing import Dict, Sequence

ARCHIVE = pathlib.Path(__file__).resolve().parent.parent / "algorithms" / "original"
MANIFEST = ARCHIVE / "FROZEN.sha256"
FILES = [
    "balanced_iterative.py",
    "balanced_recursive.py",
    "dominator_iterative.py",
    "dominator_recursive.py",
]

BANNER = """# SHA-256 digests of the four archived submissions.
# Written by tools/freeze_archive.py; verified by tests/test_original_characterization.py.
# If a digest changes, somebody edited the archive. Revert the edit -- do not 'fix' this file.
"""


def digests() -> Dict[str, str]:
    return {name: hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest() for name in FILES}


def render() -> str:
    lines = [BANNER.rstrip("\n"), ""]
    for name, digest in digests().items():
        lines.append(f"{digest}  {name}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)

    expected = render()
    if args.check:
        if not MANIFEST.exists():
            print("algorithms/original/FROZEN.sha256 is missing", file=sys.stderr)
            return 1
        if MANIFEST.read_text() != expected:
            print("the archive does not match FROZEN.sha256", file=sys.stderr)
            return 1
        print("archive digests match")
        return 0

    MANIFEST.write_text(expected)
    print(f"wrote {MANIFEST.relative_to(ARCHIVE.parent.parent)}")
    for name, digest in digests().items():
        print(f"  {digest[:16]}...  {name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
