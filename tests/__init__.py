"""Tests for the balanced-string package.

The suite is organised by *what would go wrong if it were missing*:

* ``test_balanced_core.py``            -- the definition itself, and the input policy
* ``test_balanced_implementations.py`` -- every implementation agrees with the
  oracle, exhaustively for short strings, randomly for longer ones
* ``test_contracts.py``                -- the archived programs, side by side, and
  the exact places where they disagree with the contract and with each other
* ``test_original_characterization.py``-- the archived bugs, locked down
* ``test_recursion.py``                -- recursion depth, limits and the way out
* ``test_dominator_implementations.py``-- the four dominator strategies
* ``test_tracing.py``                  -- the instrumentation the docs rely on
* ``test_support.py``                  -- ReadCounter / run_deep / tables
* ``test_docs_traces.py``              -- the traces quoted in docs/ are current

Run everything with::

    python -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import os
import sys

# Make `import algorithms` work no matter where the tests are started from.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
