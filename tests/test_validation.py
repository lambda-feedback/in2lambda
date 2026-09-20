"""Tests for the checks run over a question set before it is exported.

Each folder in ``fixtures/problems`` is a hand-written export exhibiting one problem,
beside the report it should produce, so covering another check means adding a folder
rather than a test. The real exports in ``fixtures/exports`` are the other half of it:
whatever the validator reports, it must not report a set the platform itself wrote.

The markdown cases were ported from ``conversion2025/tools and testing/validator_tests.py``
on the ``Summer2025`` branch.
"""

import shutil
from pathlib import Path

import pytest
from conftest import EXPORTS, PROBLEM_SETS

from in2lambda.api.set import Set
from in2lambda.validation import MathDelimiterError, pdf, validate

E = MathDelimiterError

needs_compiler = pytest.mark.skipif(
    bool(pdf.missing_tools()),
    reason="compiling the set as the PDF generator does needs pandoc and xelatex",
)
"""The fixtures are reported with the PDF generator's toolchain installed; CI has it."""

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


def _messages(markdown: str) -> list[str]:
    """What the validator says about a single piece of markdown."""
    question_set = Set()
    question_set.add_question("Markdown", markdown)
    return [problem.message for problem in validate(question_set, compile=False)]


@needs_compiler
@pytest.mark.parametrize("problem_set", PROBLEM_SETS, ids=lambda path: path.name)
def test_expected_problems_are_reported(problem_set: Path) -> None:
    """Each hand-written export produces exactly the report written beside it."""
    expected = (problem_set / "expected.txt").read_text().splitlines()
    found = validate(Set.from_json(str(problem_set)))

    assert sorted(str(problem) for problem in found) == sorted(expected)


@needs_compiler
@pytest.mark.parametrize("export", EXPORTS, ids=lambda path: path.name)
def test_real_exports_have_no_problems(export: Path) -> None:
    """A set the platform wrote and accepted back must never be reported."""
    assert validate(Set.from_json(str(export))) == []


@pytest.mark.parametrize("content", VALID)
def test_valid_markdown_passes(content: str) -> None:
    assert _messages(content) == []


@pytest.mark.parametrize("content, expected", INVALID)
def test_invalid_markdown_is_reported(
    content: str, expected: MathDelimiterError
) -> None:
    assert _messages(content) == [expected.value]


def test_image_that_is_not_on_disk_is_reported(tmp_path: Path) -> None:
    """An image a question lists but that is not there would break the export."""
    question_set = Set()
    question_set.add_question("Rocket", "![pictureTag](rocket.png)")
    question_set.current_question.images.append(str(tmp_path / "rocket.png"))

    assert [problem.message for problem in question_set.problems(compile=False)] == [
        f"there is no image file at {tmp_path / 'rocket.png'}"
    ]


def test_missing_compiler_says_what_to_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the PDF generator's toolchain, the set is not compiled but is reported."""
    monkeypatch.setattr(shutil, "which", lambda tool: None)
    question_set = Set()
    question_set.add_question("Angles", "Turn through 90°.")

    problems = validate(question_set)

    assert len(problems) == 1
    assert "xelatex" in problems[0].message
    assert "texlive-xetex" in problems[0].message
