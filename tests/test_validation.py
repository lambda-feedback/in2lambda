"""Tests for the math-delimiter checker.

Ported from ``conversion2025/tools and testing/validator_tests.py`` on the
``Summer2025`` branch and adapted to the :class:`MathDelimiterError` enum.
"""

import pytest

from in2lambda.validation import (
    MathDelimiterError,
    check_markdown,
    math_delimiter_checker,
)

E = MathDelimiterError

VALID = [
    "This is an inline math expression: $x = y$.",
    "This is an inline math expression: $x = y$",
    "$x = y$, this is an inline math expression.",
    "$x = y$\n",
    "\n$x = y$",
    "First expression $x = y$ and second expression $a = b$.",
    "Expression: $\\alpha + \\beta = \\gamma$.",
    "This is a display math expression:\n$$\nx = y\n$$",
    "$$\nx = y\n$$\n, this is a display math expression.",
    "Display math:\n$$\nx = y\n\na = b\n$$",
    "Expression:\n$$\n$$",
    "Inline $x = y$ and display math:\n$$\nx = y\n$$",
    "First:\n$$\nx = y\n$$\nSecond:\n$$\na = b\n$$",
    "",
    "This is just regular text with no math expressions.",
    "This costs \\$5 and that costs \\$10.",
    "Price is \\$10 and math is $x = y$.",
    "Price \\$100:\n$$\nx = y\n$$",
    "This symbol \\$\\$ is not math.",
    "\\$100 is expensive.",
    "It costs \\$",
    "Price \\$50 for $x + y = z$ calculation.",
    "Expression: $cost = \\$100$.",
    "Display:\n$$\ncost = \\$100\n$$",
]

INVALID = [
    ("This is an inline math expression: $x = y.", E.MISSING_CLOSING_SINGLE_DOLLAR),
    ("This is an inline math expression: x = y$.", E.MISSING_CLOSING_SINGLE_DOLLAR),
    ("This is an inline math expression:$x \n= y$.", E.INVALID_NEWLINE_INSIDE_INLINE),
    ("This is an inline math expression:$\nx = y$.", E.INVALID_NEWLINE_INSIDE_INLINE),
    ("This is an inline math expression:$x = y\n$.", E.INVALID_NEWLINE_INSIDE_INLINE),
    ("Expression $x = y$$.", E.DOUBLE_DOLLAR_INSTEAD_OF_CLOSING_SINGLE),
    ("Expression $x = y$ and $a = b$ and $c =", E.MISSING_CLOSING_SINGLE_DOLLAR),
    ("Expression $$$x = y$$$.", E.MISSING_NEWLINE_BEFORE_OPENING_DISPLAY),
    (
        "This is a display math expression:\n$$\nx = y\n",
        E.MISSING_CLOSING_DOUBLE_DOLLAR,
    ),
    (
        "This is a display math expression:\nx = y\n$$",
        E.MISSING_NEWLINE_AFTER_OPENING_DISPLAY,
    ),
    (
        "This is a display math expression:$$\nx = y\n$$.",
        E.MISSING_NEWLINE_BEFORE_OPENING_DISPLAY,
    ),
    (
        "This is a display math expression:\n$$\nx = y\n$$.",
        E.MISSING_NEWLINE_AFTER_CLOSING_DISPLAY,
    ),
    ("Expression:\n$$text\nx = y\n$$", E.MISSING_NEWLINE_AFTER_OPENING_DISPLAY),
    ("Expression:\n$$\nx = y\ntext$$", E.MISSING_NEWLINE_BEFORE_CLOSING_DISPLAY),
    ("Expression $$x = y$.", E.MISSING_NEWLINE_BEFORE_OPENING_DISPLAY),
    ("Expression $x = y$$", E.DOUBLE_DOLLAR_INSTEAD_OF_CLOSING_SINGLE),
    ("Expression $$x = y$", E.MISSING_NEWLINE_BEFORE_OPENING_DISPLAY),
]


@pytest.mark.parametrize("content", VALID)
def test_valid_markdown_passes(content: str) -> None:
    assert math_delimiter_checker(content) is E.PASSED
    assert check_markdown(content) == []


@pytest.mark.parametrize("content, expected", INVALID)
def test_invalid_markdown_is_reported(
    content: str, expected: MathDelimiterError
) -> None:
    assert math_delimiter_checker(content) is expected
    assert check_markdown(content) == [expected]
