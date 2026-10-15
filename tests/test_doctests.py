"""Run every docstring example in the repository.

    python -m unittest tests.test_doctests

``unittest discover`` picks this module up like any other, so a docstring example
in ``algorithms/`` or ``tools/`` is as checked as an assertion in the rest of the
suite.  That matters more than it sounds: a docstring is documentation, and
documentation that is not executable drifts.  (This repository caught itself
doing exactly that: ``docs/00`` used to claim the examples were run by
``python -m doctest algorithms/...``, which cannot import a module that uses
relative imports.  The claim is now true, and this file is why.)

Examples tagged ``# doctest: +SKIP`` are deliberately not run -- they are the
ones that print a whole rendered table for a human to read, where the value is
the picture rather than the assertion.  The same tables are drift-checked by
``tests/test_docs_traces.py`` instead.
"""

from __future__ import annotations

import doctest
import importlib
import pkgutil
import unittest
from typing import Iterator, List

import algorithms
import tools

__all__ = ["MODULES", "load_tests", "TestDoctestsAreStillThere"]

#: Whitespace is normalised and ``...`` is allowed, so an example can quote a
#: rendered table without depending on the exact padding of every line.
FLAGS = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS


def _modules() -> Iterator[str]:
    """Every importable module under ``algorithms/`` and ``tools/``."""
    for package in (algorithms, tools):
        yield package.__name__
        for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            yield info.name


MODULES: List[str] = sorted(_modules())


def load_tests(loader, tests, ignore):  # noqa: ANN001 - unittest's protocol
    """Attach one ``DocTestSuite`` per module to the discovered suite."""
    for name in MODULES:
        module = importlib.import_module(name)
        tests.addTests(doctest.DocTestSuite(module, optionflags=FLAGS))
    return tests


class TestDoctestsAreStillThere(unittest.TestCase):
    """Guard against the suite passing because it found nothing to run."""

    def test_every_module_is_importable(self):
        for name in MODULES:
            with self.subTest(module=name):
                self.assertTrue(importlib.import_module(name) is not None)

    def test_the_examples_did_not_disappear(self):
        found = 0
        for name in MODULES:
            module = importlib.import_module(name)
            found += len(doctest.DocTestFinder().find(module))
        self.assertGreaterEqual(found, 40, f"only {found} docstring examples found")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
