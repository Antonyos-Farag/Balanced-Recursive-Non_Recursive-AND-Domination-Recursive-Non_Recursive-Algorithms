"""Every balanced-string implementation must agree with the oracle.

Two kinds of checking live here:

**Exhaustive** -- every string over a small alphabet, up to a length that covers
every structural case (a third letter appearing, letters separated by gaps, ties
between different pairs).  Exhaustive tests are worth the milliseconds: they do
not need a random seed, they cannot be flaky, and when they fail the
counterexample is printed by name.

**Randomised** -- long strings, to reach sizes the exhaustive pass cannot.

The oracle is ``reference``, the O(n^3) "try every substring" function.  If a
test here fails, the fast implementation is wrong, not the oracle -- and if you
suspect the oracle, ``test_the_oracle_agrees_with_a_second_opinion`` checks it
against a second, independently written definition.
"""

from __future__ import annotations

import itertools
import random
import unittest

from algorithms import balanced
from algorithms.balanced.core import is_balanced, normalize

IMPLEMENTATIONS = balanced.IMPLEMENTATIONS


def oracle(s: str):
    """A second, deliberately different oracle: build every substring's counts."""
    best = 0
    answers = set()
    n = len(s)
    for start in range(n):
        counts = {}
        for end in range(start, n):
            ch = s[end]
            counts[ch] = counts.get(ch, 0) + 1
            if len(counts) == 2:
                values = list(counts.values())
                if values[0] == values[1]:
                    length = end - start + 1
                    if length > best:
                        best, answers = length, {s[start : end + 1]}
                    elif length == best:
                        answers.add(s[start : end + 1])
    return best, sorted(answers)


class TestOracle(unittest.TestCase):
    def test_the_oracle_agrees_with_a_second_opinion(self):
        for text in ["aabbc", "abcabc", "ababab", "aab", "abba", "zz", "aaabbb", ""]:
            with self.subTest(text=text):
                self.assertEqual(balanced.reference(text), oracle(text))

    def test_the_oracle_agrees_exhaustively_on_short_strings(self):
        for length in range(0, 7):
            for letters in itertools.product("abc", repeat=length):
                text = "".join(letters)
                with self.subTest(text=text):
                    self.assertEqual(balanced.reference(text), oracle(text))


class TestAgreementExhaustive(unittest.TestCase):
    """Small alphabets, every string: the definitive correctness check."""

    def _check(self, text: str) -> None:
        expected = balanced.reference(text)
        for name, function in IMPLEMENTATIONS.items():
            with self.subTest(text=text, implementation=name):
                self.assertEqual(function(text), expected)

    def test_all_strings_over_two_letters_up_to_length_10(self):
        for length in range(0, 11):
            for letters in itertools.product("ab", repeat=length):
                self._check("".join(letters))

    def test_all_strings_over_three_letters_up_to_length_8(self):
        for length in range(0, 9):
            for letters in itertools.product("abc", repeat=length):
                self._check("".join(letters))

    def test_all_strings_over_four_letters_up_to_length_6(self):
        for length in range(0, 7):
            for letters in itertools.product("abcd", repeat=length):
                self._check("".join(letters))


class TestAgreementRandomised(unittest.TestCase):
    def test_random_short_and_medium_strings(self):
        rng = random.Random(20240517)
        for _ in range(300):
            length = rng.randint(0, 60)
            alphabet = rng.choice(["ab", "abc", "abcde", "abcdefghijklmnopqrstuvwxyz"])
            text = "".join(rng.choice(alphabet) for _ in range(length))
            expected = balanced.reference(text)
            for name, function in IMPLEMENTATIONS.items():
                with self.subTest(text=text, implementation=name):
                    self.assertEqual(function(text), expected)

    def test_adversarial_shapes(self):
        """Patterns designed to break the "a third letter appears" intuition."""
        cases = [
            "ab" * 20,  # never a third letter
            "ab" * 20 + "c",
            "abcdefghijklmnopqrstuvwxyz" * 2,
            "a" * 50 + "b" * 50,
            "a" * 60,
            "aabb" * 15,
            "aaabbbcccaaabbb",
            "abcabcabcabcabcabc",
        ]
        for text in cases:
            expected = balanced.reference(text)
            for name, function in IMPLEMENTATIONS.items():
                with self.subTest(text=text, implementation=name):
                    self.assertEqual(function(text), expected)

    def test_longer_inputs_where_the_quadratic_versions_still_apply(self):
        rng = random.Random(99)
        text = "".join(rng.choice("abc") for _ in range(400))
        expected = balanced.reference(text)
        for name in ["brute_force", "round_trip", "pair_scan"]:
            with self.subTest(implementation=name):
                self.assertEqual(IMPLEMENTATIONS[name](text), expected)


class TestKnownAnswers(unittest.TestCase):
    """Hand-checked answers, so the suite does not only test self-consistency."""

    def test_the_submission_examples(self):
        # Both archived programs, run on "aabbb" and "abcabc", are used as the
        # running examples in docs/01-balanced-strings.md.  These are the
        # answers a *correct* implementation must give.
        self.assertEqual(balanced.brute_force("aabbb"), (4, ["aabb"]))
        self.assertEqual(balanced.brute_force("abcabc"), (2, ["ab", "bc", "ca"]))
        self.assertEqual(balanced.brute_force("aabbc"), (4, ["aabb"]))

    def test_every_answer_really_is_balanced(self):
        rng = random.Random(5)
        for _ in range(100):
            text = "".join(rng.choice("abcd") for _ in range(rng.randint(0, 40)))
            length, answers = balanced.pair_scan(text)
            for answer in answers:
                self.assertEqual(len(answer), length)
                self.assertTrue(is_balanced(answer))
                self.assertIn(answer, text)

    def test_answers_are_sorted_and_unique(self):
        length, answers = balanced.pair_scan("abcabc")
        self.assertEqual(answers, sorted(set(answers)))

    def test_no_longer_answer_exists(self):
        """Cross-check the length claim against every window, independently."""
        rng = random.Random(6)
        for _ in range(50):
            text = "".join(rng.choice("abc") for _ in range(rng.randint(0, 25)))
            length, _answers = balanced.pair_scan(text)
            for start in range(len(text)):
                for end in range(start + length + 1, len(text) + 1):
                    window = text[start:end]
                    self.assertFalse(
                        is_balanced(window),
                        msg=f"{window!r} is balanced and longer than {length} in {text!r}",
                    )


class TestInputPolicy(unittest.TestCase):
    def test_uppercase_is_folded(self):
        self.assertEqual(balanced.pair_scan("AaBb"), balanced.pair_scan("aabb"))

    def test_casefold_off_rejects_uppercase(self):
        for name in IMPLEMENTATIONS:
            with self.subTest(implementation=name):
                with self.assertRaises(ValueError):
                    IMPLEMENTATIONS[name]("AAbb", casefold=False)

    def test_bad_input_is_rejected_loudly_by_every_implementation(self):
        for name, function in IMPLEMENTATIONS.items():
            with self.subTest(implementation=name):
                with self.assertRaises(ValueError):
                    function("a1b")
                with self.assertRaises(ValueError):
                    function("a b")
                with self.assertRaises(TypeError):
                    function(42)  # type: ignore[arg-type]

    def test_none_is_accepted_everywhere_and_means_empty(self):
        for name, function in IMPLEMENTATIONS.items():
            with self.subTest(implementation=name):
                self.assertEqual(function(None), (0, []))

    def test_normalize_is_the_only_place_validation_happens(self):
        self.assertEqual(normalize("AbC"), "abc")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
