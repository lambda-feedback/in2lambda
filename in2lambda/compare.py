r"""Compares two sets question by question, naming every place they say something else.

`in2lambda convert` writes a set, `in2lambda build` writes a set from a draft, and Lambda
Feedback exports a set. :func:`differences` compares any two of them in question and part
order - each question's main text, and each part's text and worked solution - and returns
one line per difference, naming the question, the part and the field as
`in2lambda.validation` names them.

These differences in wording are not differences in what a question says, and are taken
off both sides before comparing:

- **Whitespace.** Every run of whitespace is compared as one space, because a draft
  quotes the lines pandoc wrapped where `in2lambda convert` writes a paragraph on one
  line.
- **Separator lines.** A line holding nothing but three or more hyphens is dropped,
  because Lambda Feedback writes one around a display maths block where a document
  writes nothing.
- **Quotes.** ``‘`` and ``’`` are compared as ``'``, and ``“`` and ``”`` as ``"``,
  because pandoc's LaTeX reader writes the curly quote where its commonmark_x writer
  writes the straight one.
- **Maths notation.** Inside every ``$ ... $`` and ``$$ ... $$``, ``\left`` and
  ``\right`` are removed, ``~``, ``\,`` and ``\space`` are compared as a space, and
  every run of whitespace is dropped, except that a run between a control word and a
  following letter is compared as one space. LaTeX renders ``$z=2+3 i$`` and
  ``$z=2+3i$`` the same, and ``\mathrm{~m}`` and ``\mathrm{m}`` the same, where
  ``\alpha x`` and ``\alphax`` are two different expressions. An export writes
  ``$z = 2+3 i$`` where `in2lambda convert` writes ``$z=2+3i$``.
- **Image references.** An image is compared by the file's name, because
  `in2lambda convert` writes every image as ``![pictureTag](path)`` where a draft keeps
  the alt text the document wrote, and an export names each file as ``media/`` holds it
  where the set `in2lambda convert` returns holds the path the document wrote.
- **A lone empty part.** A single part holding neither text nor a worked solution is
  dropped from both sides, because a question written without parts or solution exports
  as one part holding nothing, where `in2lambda convert` writes no part at all.

:func:`known` reads the differences two sets are known to have from a file: one line per
difference as :func:`differences` words it, with the ticket that would close it written
after ``  # ``.
"""

import re
from itertools import zip_longest
from pathlib import Path
from typing import Any, Optional

from in2lambda.api.question import Question
from in2lambda.api.set import Set
from in2lambda.json_convert.json_convert import _IMAGE
from in2lambda.validation import _COMMAND, _MATHS, _location

_TICKET = "  # "
"""What a line of a differs.txt names the ticket closing it after."""

_RULE = re.compile(r"(?m)^[ \t]*-{3,}[ \t]*$")
"""A line holding nothing but hyphens, which is the separator Lambda Feedback writes."""

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
"""Each curly quote and the straight quote it is compared as."""

_SIZE = re.compile(r"\\(?:left|right)(?![a-zA-Z])")
r"""``\left`` and ``\right``, which size a delimiter without changing which it is."""

_LATEX_SPACE = re.compile(r"~|\\,|\\space(?![a-zA-Z])")
"""The three ways of writing a space inside maths."""

_SPACING = re.compile(rf"({_COMMAND.pattern})\s+(?=[a-zA-Z])|\s+")
"""A run of whitespace inside maths, with the control word it ends where one precedes it
and a letter follows it."""


def _spacing(whitespace: re.Match[str]) -> str:
    r"""One space where a run of whitespace ends a control word, and nothing elsewhere.

    ``\alpha x`` is two symbols and ``\alphax`` is a control word nothing defines, so
    the space between a control word and a letter is the only whitespace LaTeX renders.
    """
    return f"{whitespace[1]} " if whitespace[1] else ""


def _maths(expression: re.Match[str]) -> str:
    """One ``$ ... $`` or ``$$ ... $$`` with the notation that is not the maths folded.

    Args:
        expression: A match of `in2lambda.validation._MATHS`, holding the display maths
            it found in its first group and the inline maths in its second.
    """
    display = expression[1] is not None
    tex = expression[1] if display else expression[2]
    delimiter = "$$" if display else "$"
    folded = _LATEX_SPACE.sub(" ", _SIZE.sub("", tex))
    return f"{delimiter}{_SPACING.sub(_spacing, folded)}{delimiter}"


def _text(markdown: str) -> str:
    """A field with the differences in wording that are not differences taken off.

    A separator line is dropped, each curly quote becomes a straight quote, the maths
    notation inside every ``$ ... $`` and ``$$ ... $$`` is folded, every image reference
    is written as the file's name alone, and every run of whitespace becomes one space.
    The module docstring says why.
    """
    # Before the whitespace collapse below, which writes the field on one line and
    # leaves no line for _RULE to match.
    without_rules = _RULE.sub("", markdown)
    folded = _MATHS.sub(_maths, without_rules.translate(_QUOTES))
    named = _IMAGE.sub(lambda reference: f"![]({Path(reference[1]).name})", folded)
    return " ".join(named.split())


def _parts(question: Question) -> list[tuple[str, str]]:
    """Each part's text and worked solution, dropping a lone part holding neither."""
    parts = [(_text(part.text), _text(part.worked_solution)) for part in question.parts]
    return [] if parts == [("", "")] else parts


def _only(left: Optional[Any], thing: str, left_name: str, right_name: str) -> str:
    """Which of the two sets holds a question or a part the other one does not."""
    if left is None:
        return f"{right_name} wrote this {thing} and {left_name} did not"
    return f"{left_name} wrote this {thing} and {right_name} did not"


def _differing(
    where: str, left: str, right: str, left_name: str, right_name: str
) -> list[str]:
    """The line naming a field the two sets write differently, or no line at all."""
    if left == right:
        return []
    return [f"{where}: {left_name} says {left!r} and {right_name} says {right!r}"]


def differences(
    built: Set,
    expected: Set,
    left_name: str = "the draft",
    right_name: str = "convert",
) -> list[str]:
    r"""Every place the two sets say something different, in question and part order.

    Args:
        built: The set being checked, such as the one `in2lambda build` wrote.
        expected: The set it should reproduce, such as a Lambda Feedback export.
        left_name: What to call `built` in each line.
        right_name: What to call `expected` in each line.

    Returns:
        One line per difference, naming the question, the part and the field as
        `in2lambda.validation` names them and quoting what each set says there.

    Examples:
        >>> from in2lambda.api.set import Set
        >>> from in2lambda.compare import differences
        >>> built, expected = Set(), Set()
        >>> built.add_question(main_text="The rocket  is at\n45 degrees.")
        >>> expected.add_question(main_text="The rocket is at 45 degrees.")
        >>> differences(built, expected)
        []
        >>> expected.add_question(main_text="Find the impulse.")
        >>> differences(built, expected)
        ['Question 2 "": convert wrote this question and the draft did not']
    """
    found = []
    questions = zip_longest(built.questions, expected.questions)
    for number, (built_question, expected_question) in enumerate(questions, start=1):
        if built_question is None or expected_question is None:
            found.append(
                f"{_location(number, '')}: "
                f"{_only(built_question, 'question', left_name, right_name)}"
            )
            continue
        found += _differing(
            _location(number, "", field="main text"),
            _text(built_question.main_text),
            _text(expected_question.main_text),
            left_name,
            right_name,
        )
        parts = zip_longest(_parts(built_question), _parts(expected_question))
        for index, (built_part, expected_part) in enumerate(parts):
            if built_part is None or expected_part is None:
                found.append(
                    f"{_location(number, '', index)}: "
                    f"{_only(built_part, 'part', left_name, right_name)}"
                )
                continue
            for field, built_value, expected_value in zip(
                ("text", "worked solution"), built_part, expected_part
            ):
                found += _differing(
                    _location(number, "", index, field),
                    built_value,
                    expected_value,
                    left_name,
                    right_name,
                )
    return found


def known(path: str | Path) -> list[str]:
    """The differences two sets are known to have, as a differs.txt file holds them.

    Args:
        path: The file to read. A file that does not exist names no difference, so that
            a folder of fixtures holds one only where the two sets differ.

    Returns:
        Each line as :func:`differences` words it, with the ticket written after ``  # ``
        taken off and blank lines dropped.
    """
    path = Path(path)
    if not path.is_file():
        return []
    return [
        line.split(_TICKET)[0] for line in path.read_text().splitlines() if line.strip()
    ]
