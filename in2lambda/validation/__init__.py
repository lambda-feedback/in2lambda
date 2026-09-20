"""Checks a question set for what Lambda Feedback would refuse or render wrongly.

A question can be valid JSON and still fail to import, or import and then render wrongly:
an answer that does not fit the box marking it, an image the export will not contain,
maths KaTeX cannot render. An author otherwise finds this out by uploading the set and
reading it.

The checks report and never refuse: :func:`validate` returns the problems it found, and
in2lambda writes the export, because an author may have intended a problem.

KaTeX renders the maths, which needs Node.js, and the set is compiled as the PDF generator
compiles it, which needs pandoc and xelatex. Both are optional. Without Node.js,
:func:`validate` skips the maths check and warns that it did. Without pandoc and xelatex,
:mod:`in2lambda.validation.pdf` names the packages to install.
"""

import json
import re
import shutil
import subprocess
import warnings
from functools import cache
from pathlib import Path
from typing import NamedTuple

from in2lambda.api.problem import Problem
from in2lambda.api.question import Question
from in2lambda.api.response_area import ResponseArea
from in2lambda.api.set import Set
from in2lambda.json_convert.json_convert import _IMAGE, _image_for
from in2lambda.katex_convert.katex_convert import unsupported_commands
from in2lambda.validation import pdf
from in2lambda.validation.delimiters import MathDelimiterError, math_delimiter_checker

__all__ = ["MathDelimiterError", "Problem", "math_delimiter_checker", "validate"]

_MATHS = re.compile(r"(?<!\\)\$\$(.*?)(?<!\\)\$\$|(?<!\\)\$(.*?)(?<!\\)\$", re.DOTALL)
"""Display maths first, so that ``$$ ... $$`` is not read as two empty ``$ ... $``."""

_COMMAND = re.compile(r"\\[a-zA-Z]+")

_DEGREES = re.compile(r"\^\s*\{?\s*\\circ")
"""``^\\circ``, with or without braces around it."""

_CHECK = Path(__file__).parent / "katex" / "check.js"
"""The Node script that renders expressions with the KaTeX packaged beside it."""


class _Expression(NamedTuple):
    """One piece of maths to render, and where in the set it was written."""

    location: str
    start: int
    """Where the expression, opening delimiter included, begins in its field, from 1."""
    end: int
    tex: str
    display: bool


def _location(
    number: int, title: str, part: int | None = None, field: str | None = None
) -> str:
    """Where in a set something is, as every message here names it.

    This function is the one place that naming is written, because
    `in2lambda.draft.export` reads it backwards to find the field of a draft a problem
    was reported against.

    Args:
        number: The question's number, from 1.
        title: The question's title, quoted even where the title is empty.
        part: Which part of the question, from 0, or None for the question itself.
        field: Which field - ``main text``, ``worked solution`` - or None for the
            question or the part as a whole.
    """
    where = f'Question {number} "{title}"'
    if part is not None:
        where += f", part ({chr(ord('a') + part)})"
    if field is not None:
        where += f", {field}"
    return where


def validate(question_set: Set, compile: bool = True) -> list[Problem]:
    r"""Everything in2lambda can tell is wrong with a set, in the order it is written.

    Args:
        question_set: The set about to be exported.
        compile: Whether to compile the set as well, as Lambda Feedback's PDF generator
            compiles it, which needs pandoc and xelatex - see
            :mod:`in2lambda.validation.pdf`.

    Returns:
        One :class:`~in2lambda.api.problem.Problem` per problem found, each naming the
        question, the part and the field to read, in the order they are written. What
        KaTeX refused comes last, because in2lambda renders the whole set in one process.
        An empty list means these checks found nothing, and not that the set will import:
        they find some mistakes and not others.

    Examples:
        >>> from in2lambda.api.set import Set
        >>> from in2lambda.validation import validate
        >>> s = Set()
        >>> s.add_question("Angles", "Turn through $90^\\circ$.")
        >>> [str(problem) for problem in validate(s, compile=False)]
        ['Question 1 "Angles", main text: ^\\circ does not display; write the degree sign ° instead']
    """
    problems: list[Problem] = []
    # Every markdown field with the location to report it against, collected so that the
    # whole set compiles in one run and not a field at a time. The maths is collected the
    # same way, and rendered in one Node process.
    fields: list[tuple[str, str]] = []
    images: list[str] = []
    expressions: list[_Expression] = []

    def check(
        markdown: str, question: Question, location: str, compiled: bool = True
    ) -> list[Problem]:
        if compiled:
            fields.append((location, markdown))
        return _markdown_problems(markdown, question, location, expressions)

    for number, question in enumerate(question_set.questions, start=1):
        title = question.title
        where = _location(number, title)
        problems += check(
            question.main_text, question, _location(number, title, field="main text")
        )

        images += question.images
        for image in question.images:
            if not Path(image).is_file():
                problems.append(Problem(where, f"there is no image file at {image}"))

        for index, part in enumerate(question.parts):
            part_where = _location(number, title, index)
            for field, markdown in (
                ("text", part.text),
                ("worked solution", part.worked_solution),
                ("answer", part.answer),
            ):
                problems += check(
                    markdown, question, _location(number, title, index, field)
                )

            for area_number, area in enumerate(part.response_areas, start=1):
                area_where = f"{part_where}, answer box {area_number}"
                problems += [
                    Problem(area_where, message) for message in _area_problems(area)
                ]
                # An answer box reaches the PDF only where it is marked to, so LaTeX in a
                # box left out breaks no compile.
                for field, markdown in (
                    ("pre_text", area.pre_text),
                    ("post_text", area.post_text),
                    ("content_after", area.content_after),
                ):
                    problems += check(
                        markdown,
                        question,
                        f"{area_where}, {field}",
                        area.include_in_pdf,
                    )
                options = (area.config or {}).get("options")
                if isinstance(options, list):
                    for option_number, option in enumerate(options, start=1):
                        problems += check(
                            option,
                            question,
                            f"{area_where}, option {option_number}",
                            area.include_in_pdf,
                        )

    if compile:
        problems += pdf.problems(fields, images)

    return problems + _katex_rejections(expressions)


def _markdown_problems(
    markdown: str,
    question: Question,
    location: str,
    expressions: list[_Expression],
) -> list[Problem]:
    """Every problem in one markdown field, reported against `location`.

    The question is needed because an image reference is good only where that image is
    one of the question's, and so is written into the export's ``media/``.

    The field's maths is appended to `expressions` and not rendered here, so that the
    whole set takes one Node process and not one per field.
    """
    problems: list[Problem] = []

    delimiters = math_delimiter_checker(markdown)
    if delimiters is not MathDelimiterError.PASSED:
        problems.append(Problem(location, delimiters.value))

    # The writer rewrites a reference to the name of the image it matches, and copies
    # that image into media/. A reference matching no image is written as it stands, and
    # Lambda Feedback does not find it.
    for reference in _IMAGE.findall(markdown):
        if _image_for(reference, question.images) is None:
            problems.append(
                Problem(location, f"the export will not contain the image {reference}")
            )

    problems += _katex_problems(markdown, location, expressions, delimiters)
    return problems


def _katex_problems(
    markdown: str,
    location: str,
    expressions: list[_Expression],
    delimiters: MathDelimiterError,
) -> list[Problem]:
    """Maths that KaTeX, which Lambda Feedback renders with, will not display.

    An expression the lists say nothing about is appended to `expressions` for KaTeX
    itself to render. An expression the lists object to is not appended: their message
    names what to write instead, where KaTeX's message names the character it stopped at,
    and one fault reads better as one line.
    """
    problems: list[Problem] = []
    lacks = _katex_lacks()

    for span in _MATHS.finditer(markdown):
        display = span[1] is not None
        maths = span[1] if display else span[2]
        unsupported = [
            command for command in _COMMAND.findall(maths) if command in lacks
        ]
        for command in unsupported:
            replacement = lacks[command]
            problems.append(
                Problem(
                    location,
                    (
                        f"KaTeX does not render {command}; write {replacement} instead"
                        if replacement
                        else f"KaTeX does not render {command}"
                    ),
                )
            )
        if _DEGREES.search(maths):
            problems.append(
                Problem(
                    location,
                    "^\\circ does not display; write the degree sign ° instead",
                )
            )
        # Where the field's delimiters are wrong, the text between them may not be the
        # expression the author wrote, so KaTeX does not render it. The checks above
        # report against the field and not a character range, so they still run.
        if not unsupported and delimiters is MathDelimiterError.PASSED:
            expressions.append(
                _Expression(location, span.start() + 1, span.end(), maths, display)
            )

    return problems


def _katex_rejections(expressions: list[_Expression]) -> list[Problem]:
    """What KaTeX itself refuses to render, for the whole set in one Node process.

    Node.js is optional, because an author writing questions in Python need not install
    it. Without Node.js this one check is skipped, and the warning names what to install.
    """
    if not expressions:
        return []

    node = _node()
    if node is None:
        warnings.warn(
            "Maths was not checked against KaTeX: install Node.js "
            "(https://nodejs.org) and run again",
            stacklevel=3,
        )
        return []

    try:
        rendered = subprocess.run(
            [node, str(_CHECK)],
            input=json.dumps(
                [
                    {"tex": expression.tex, "display": expression.display}
                    for expression in expressions
                ]
            ),
            capture_output=True,
            # Not the locale's encoding: KaTeX marks where it stopped reading with
            # combining low lines, so its messages hold characters outside ASCII, and
            # Node writes them as UTF-8 whatever LANG says.
            encoding="utf-8",
            check=True,
        )
        rejections = json.loads(rendered.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        # Whatever is named node on the PATH runs here, and it may not be Node.js. These
        # checks report and never refuse, so a check that cannot run warns and leaves the
        # rest of the report, and the export, alone.
        warnings.warn(
            f"Maths was not checked against KaTeX: running {node} failed ({error})",
            stacklevel=3,
        )
        return []

    problems: list[Problem] = []
    for rejection in rejections:
        expression = expressions[rejection["index"]]
        problems.append(
            Problem(
                f"{expression.location}, characters {expression.start}-{expression.end}",
                f"KaTeX rejects it: {rejection['message']}",
            )
        )
    return problems


@cache
def _node() -> str | None:
    """Where node is installed, or None where it is not installed."""
    return shutil.which("node")


@cache
def _katex_lacks() -> dict[str, str | None]:
    """What KaTeX lacks, keyed by the command as it is written, not as a regex.

    :func:`~in2lambda.katex_convert.katex_convert.unsupported_commands` returns the lists
    as they are written, with a command's backslash escaped for the replacing pass. An
    entry that is not a single command, such as a whole environment, matches no command.
    """
    return {
        pattern.replace("\\\\", "\\"): (
            replacement.replace("\\\\", "\\") if replacement else replacement
        )
        for pattern, replacement in unsupported_commands().items()
    }


def _area_problems(area: ResponseArea) -> list[str]:
    """Where an answer box's answer does not fit the box, or does not fit what marks it.

    Only the three response type and evaluation function pairings the real exports use
    (``tests/fixtures/exports/README.md``) are checked. Any other evaluation function may
    expect an answer of any shape, and a check on one would report a fault that is none.
    """
    messages = []

    wants_list = [
        name
        for name in (area.response_type, area.evaluation_function)
        if name in ("MULTIPLE_CHOICE", "arrayEqual")
    ]
    wants_text = [
        name
        for name in (area.response_type, area.evaluation_function)
        if name
        in (
            "MATH_SINGLE_LINE",
            "NUMERIC_UNITS",
            "symbolicEqual",
            "comparePhysicalQuantities",
        )
    ]
    if wants_list and not isinstance(area.answer, list):
        messages.append(
            f"{' and '.join(wants_list)} needs one true/false answer per option, not text"
        )
    if wants_text and not isinstance(area.answer, str):
        messages.append(
            f"{' and '.join(wants_text)} needs the answer as text, not a list"
        )

    if area.response_type == "MULTIPLE_CHOICE" and isinstance(area.answer, list):
        config = area.config or {}
        options = config.get("options")
        if not isinstance(options, list):
            messages.append("multiple choice has no options to answer")
        elif len(options) != len(area.answer):
            messages.append(
                f"{len(options)} options but {len(area.answer)} true/false answers"
            )

        correct = area.answer.count(True)
        if correct == 0:
            messages.append("no option is marked correct")
        elif correct > 1 and config.get("single"):
            messages.append(
                f"{correct} options are marked correct, but only one answer is allowed"
            )

    if area.response_type in ("MATH_SINGLE_LINE", "NUMERIC_UNITS") and isinstance(
        area.answer, str
    ):
        if not area.answer.strip():
            messages.append(f"{area.response_type} has no answer")
        elif area.response_type == "NUMERIC_UNITS" and not re.search(
            r"\d", area.answer
        ):
            messages.append(f'NUMERIC_UNITS answer "{area.answer}" has no number in it')

    return messages
