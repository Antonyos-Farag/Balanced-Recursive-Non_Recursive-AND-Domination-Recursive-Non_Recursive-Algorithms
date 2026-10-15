"""Characterization tests: pin down what the archived code *actually* does.

A characterization test asserts observable behaviour, bugs included.  It is the
right tool for legacy code, and it is what makes a bug report trustworthy: the
repository does not claim "the loop version is broken" in prose, it shows a
model of the broken behaviour and proves the submission matches that model on
20,000 random inputs.

Two rules are followed here:

1. **Never "fix" the archive.**  If a test in this file fails after an edit to
   ``algorithms/original/``, the edit changed history.  Fix the edit.
2. **Say which behaviour is a bug and which is merely a policy.**  The recursive
   submission differs from the non-recursive one on non-letter input, but on
   that input it is *correct* -- it is the loop version that is wrong.  The
   comments below are careful about the difference.
"""

from __future__ import annotations

import ast
import contextlib
import inspect
import io
import itertools
import random
import unittest

from algorithms import balanced
from algorithms.balanced.core import legacy_equal_pair
from algorithms.original import balanced_iterative as legacy_loop
from algorithms.original import balanced_recursive as legacy_recursive
from algorithms.original import dominator_iterative as legacy_vote
from algorithms.original import dominator_recursive as legacy_dc


def _sorted(result):
    """Compare order-insensitively: discovery order is not part of any contract."""
    return result[0], sorted(result[1])


def model_of_the_loop_submission(s: str):
    """What the misplaced balance check computes, written out on purpose.

    For every ``start`` the submission scans forward, maintaining a frequency
    table, and stops at the first third letter.  The balance test, however, runs
    *after* that scan has finished, so the only window it ever examines for a
    given ``start`` is the last one the scan touched: ``s[start:end + 1]`` where
    ``end`` is either ``len(s) - 1`` or the position of the third letter.  Every
    window in between is thrown away.

    If this model matches the submission on every input, the diagnosis "the
    check is in the wrong place" is proven rather than guessed.
    """
    n = len(s)
    best = 0
    answers = []
    for start in range(n):
        freq = [0] * 26
        distinct = 0
        end = start - 1
        for end in range(start, n):
            index = ord(s[end]) - ord("a")
            if freq[index] == 0:
                distinct += 1
            freq[index] += 1
            if distinct > 2:
                break
        if distinct == 2 and legacy_equal_pair(freq):
            window = s[start : end + 1]
            length = end - start + 1
            if length > best:
                best, answers = length, [window]
            elif length == best and window not in answers:
                answers.append(window)
    return best, answers


def _is_ascii_letter(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def model_of_the_recursive_submission(s: str):
    """The recursive submission's behaviour: correct, but blind across gaps.

    The scan stops at the first non-letter for each ``start``, so windows that
    contain a non-letter are never examined.  That costs nothing here: a
    balanced window uses exactly two distinct *letters*, so it can never contain
    a non-letter in the first place.  The recursive program is therefore
    equivalent to "solve the problem separately in each maximal run of letters".
    """
    best = 0
    answers = set()
    runs = "".join(ch if _is_ascii_letter(ch) else " " for ch in s).split()
    for run in runs:
        length, substrings = balanced.reference(run.lower())
        if length > best:
            best, answers = length, set(substrings)
        elif length == best:
            answers |= set(substrings)
    return best, sorted(answers)


class TestLoopSubmissionBalanced(unittest.TestCase):
    """``LBS_all_longest``: the check is outside the loop.  Bug B1."""

    def test_the_model_matches_the_submission_exactly(self):
        # 20,000 inputs: enough that a model which is even slightly wrong shows
        # up.  (A model that matched on ten hand-picked strings would prove
        # nothing -- the whole point is that the *diagnosis* is what is being
        # tested, not the three examples in the bug report.)
        rng = random.Random(2024)
        for _ in range(20_000):
            text = "".join(rng.choice("abcd") for _ in range(rng.randint(0, 12)))
            with self.subTest(text=text):
                self.assertEqual(legacy_loop.LBS_all_longest(text), model_of_the_loop_submission(text))

    def test_the_model_matches_on_every_short_string(self):
        for length in range(0, 8):
            for letters in itertools.product("abc", repeat=length):
                text = "".join(letters)
                with self.subTest(text=text):
                    self.assertEqual(legacy_loop.LBS_all_longest(text), model_of_the_loop_submission(text))

    def test_it_answers_zero_for_a_string_with_an_obvious_answer(self):
        # "aabbb" contains "aabb".  The submission reports nothing at all, and
        # says nothing about it: a silent wrong answer, the worst kind.
        self.assertEqual(legacy_loop.LBS_all_longest("aabbb"), (0, []))
        self.assertEqual(balanced.reference("aabbb"), (4, ["aabb"]))

    def test_the_documented_example_table(self):
        table = {
            "aabbb": (0, []),
            "aabbc": (2, ["bc"]),
            "abcabc": (2, ["bc"]),
            "aabbaa": (4, ["bbaa"]),
            "aabb": (4, ["aabb"]),
            "abab": (4, ["abab"]),
            "ababab": (6, ["ababab"]),
            "aaabbb": (6, ["aaabbb"]),
            "": (0, []),
            "a": (0, []),
        }
        for text, expected in table.items():
            with self.subTest(text=text):
                self.assertEqual(legacy_loop.LBS_all_longest(text), expected)

    def test_none_is_accepted(self):
        self.assertEqual(legacy_loop.LBS_all_longest(None), (0, []))

    def test_bad_input_prints_instead_of_raising(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = legacy_loop.LBS_all_longest("AAbb")
        self.assertEqual(result, (0, []))
        self.assertIn("only lowercase letters allowed", out.getvalue())


class TestRecursiveSubmissionBalanced(unittest.TestCase):
    """``LBS``: correct, but with three rough edges (B3, B4, B5)."""

    def test_it_is_correct_on_lowercase_input(self):
        rng = random.Random(7)
        for _ in range(2000):
            text = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(0, 30)))
            with self.subTest(text=text):
                self.assertEqual(_sorted(legacy_recursive.LBS(text)), _sorted(balanced.reference(text)))

    def test_it_is_correct_on_uppercase_input(self):
        rng = random.Random(8)
        for _ in range(1000):
            text = "".join(rng.choice("aAbBcC") for _ in range(rng.randint(0, 20)))
            with self.subTest(text=text):
                self.assertEqual(
                    _sorted(legacy_recursive.LBS(text)), _sorted(balanced.reference(text.lower()))
                )

    def test_non_letters_are_a_wall_and_it_does_not_matter(self):
        """Bug B5 -- a policy difference that costs nothing.

        Windows containing a non-letter are never examined, but a balanced
        window can never contain one, so the answers are still complete.  The
        only real problem is that the caller is never *told* what happened.
        """
        rng = random.Random(9)
        for _ in range(2000):
            text = "".join(rng.choice("abc11..!!") for _ in range(rng.randint(0, 20)))
            with self.subTest(text=text):
                self.assertEqual(_sorted(legacy_recursive.LBS(text)), model_of_the_recursive_submission(text))

    def test_non_ascii_letters_crash_it(self):
        # 'e'.isalpha() is True for 'e-acute', so the guard lets it through and
        # then freq[136] blows up.  Bug B3.
        self.assertTrue("\u00e9".isalpha())
        with self.assertRaises(IndexError):
            legacy_recursive.LBS("caf\u00e9")
        with self.assertRaises(IndexError):
            legacy_recursive.LBS("Stra\u00dfe")

    def test_long_input_hits_the_recursion_limit(self):
        # Bug B4: depth grows with the window, so ~996 characters is the wall.
        with self.assertRaises(RecursionError):
            legacy_recursive.LBS("a" * 2000)
        self.assertEqual(legacy_recursive.LBS("a" * 900), (0, []))

    def test_empty_and_tiny_inputs(self):
        self.assertEqual(legacy_recursive.LBS(""), (0, []))
        self.assertEqual(legacy_recursive.LBS("a"), (0, []))
        self.assertEqual(legacy_recursive.LBS("ab"), (2, ["ab"]))


class TestLoopSubmissionDominator(unittest.TestCase):
    """``dominator``: right answer, awkward contract.  Bug B8."""

    def test_no_dominator_is_minus_one(self):
        self.assertEqual(legacy_vote.dominator([]), -1)
        self.assertEqual(legacy_vote.dominator([1, 2, 3, 4]), -1)

    def test_a_dominator_is_a_list_of_indices(self):
        self.assertEqual(legacy_vote.dominator([3, 1, 3, 2, 3, 4, 3, 3]), [0, 2, 4, 6, 7])
        self.assertEqual(legacy_vote.dominator([2]), [0])

    def test_the_single_element_case_is_not_what_the_comment_promised(self):
        # The archived driver printed [2] for A = [2] while its comment talked
        # about [0, 2, 4, 6, 7].  Bug B14: a comment that describes a different
        # array than the code runs on.
        self.assertEqual(legacy_vote.dominator([2]), [0])

    def test_it_agrees_with_the_contract_on_integer_arrays(self):
        rng = random.Random(10)
        for _ in range(2000):
            values = [rng.randint(0, 3) for _ in range(rng.randint(0, 15))]
            result = legacy_vote.dominator(values)
            expected = balanced_dominator(values)
            if result == -1:
                self.assertIsNone(expected, msg=f"{values} should have no dominator")
            else:
                self.assertEqual(list(result), list(expected.indices), msg=str(values))


def balanced_dominator(a):
    """A local copy of the contract, so this file depends on nothing else."""
    from algorithms import dominator

    return dominator.boyer_moore(a)


class TestRecursiveSubmissionDominator(unittest.TestCase):
    """``find_dominator_recursive``: solid algorithm, fragile sentinel.  B10-B13."""

    def test_it_is_correct_on_integer_arrays(self):
        rng = random.Random(11)
        for _ in range(2000):
            values = [rng.randint(0, 3) for _ in range(rng.randint(1, 15))]
            expected = balanced_dominator(values)
            got = legacy_dc.find_dominator_indices(values)
            if expected is None:
                self.assertEqual(got, [], msg=str(values))
            else:
                self.assertEqual(got, list(expected.indices), msg=str(values))

    def test_empty_array_is_empty_list(self):
        self.assertEqual(legacy_dc.find_dominator_indices([]), [])

    def test_none_as_a_value_defeats_the_sentinel(self):
        # The [None, None, 1] array *does* have a dominator: None, twice.
        # The function returns [] -- "no dominator" -- because None is its
        # internal marker for "nothing".  Bug B12.
        self.assertEqual(legacy_dc.find_dominator_indices([None, None, 1]), [])
        self.assertEqual(legacy_dc.find_dominator_indices([1, None, None]), [])
        # ...and for a two-element array it accidentally works, which is worse:
        # the bug appears and disappears depending on the input size.
        self.assertEqual(legacy_dc.find_dominator_indices([None, None]), [0, 1])

    def test_the_driver_at_the_bottom_prints_a_misleading_comment(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print(legacy_dc.find_dominator_indices([2]), "# Output: [0, 2, 4, 6, 7]")
        self.assertIn("[0]", out.getvalue())


class TestDeadCodeInTheSubmission(unittest.TestCase):
    """Static evidence for the "this line is dead" claim (bug B9).

    Claiming "``left_count`` is never read" in a document is easy; proving it
    with the ``ast`` module takes twelve lines and cannot be wrong.
    """

    def _named_loads(self, module, name):
        source = inspect.getsource(module)
        tree = ast.parse(source)
        stores = 0
        loads = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == name:
                if isinstance(node.ctx, ast.Store):
                    stores += 1
                elif isinstance(node.ctx, ast.Load):
                    loads += 1
        return stores, loads

    def test_left_count_is_written_and_never_read(self):
        stores, loads = self._named_loads(legacy_dc, "left_count")
        self.assertEqual(stores, 1, "the variable should be assigned exactly once")
        self.assertEqual(loads, 0, "if this fails, the dead code has been used -- good!")

    def test_the_other_locals_are_used(self):
        # A control: the same analysis on a variable that *is* used.
        stores, loads = self._named_loads(legacy_dc, "right_candidate")
        self.assertGreaterEqual(stores, 1)
        self.assertGreater(loads, 0)

    def test_the_archive_has_not_been_modified(self):
        """The archived files must stay byte-identical to the submission.

        ``tools/freeze_archive.py`` writes ``algorithms/original/FROZEN.sha256``;
        this test recomputes the digests and compares.  A failing digest means
        somebody edited history -- the fix is to revert the edit, not to update
        the file.  Deleting the file is also a failure, on purpose.
        """
        import hashlib
        import pathlib

        folder = pathlib.Path(inspect.getsourcefile(legacy_dc)).parent
        manifest = folder / "FROZEN.sha256"
        self.assertTrue(manifest.exists(), "run: python -m tools.freeze_archive")

        recorded = {}
        for line in manifest.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            digest, name = line.split()
            recorded[name] = digest

        self.assertEqual(
            sorted(recorded),
            [
                "balanced_iterative.py",
                "balanced_recursive.py",
                "dominator_iterative.py",
                "dominator_recursive.py",
            ],
        )
        for name, digest in recorded.items():
            actual = hashlib.sha256((folder / name).read_bytes()).hexdigest()
            with self.subTest(file=name):
                self.assertEqual(actual, digest, f"{name} was modified after archiving")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
