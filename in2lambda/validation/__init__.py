"""Checks a question set for what Lambda Feedback would refuse or render wrongly.

A question can be perfectly valid JSON and still fail to import, or import and then
look wrong: an answer that does not fit the box marking it, an image the export will
not contain, maths KaTeX cannot render. Authors otherwise find this out by uploading
and looking.

Everything here reports, never refuses: :func:`validate` returns what it found and the
export goes ahead regardless, since a problem may well be deliberate.

Maths is rendered with KaTeX itself, which needs Node.js, and the set is compiled as the
PDF generator compiles it, which needs pandoc and xelatex. Both are optional: without
Node the maths check is skipped with a warning saying so, and without the compiler
:mod:`in2lambda.validation.pdf` reports what to install.
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

    The one place that naming lives, since `in2lambda.draft.export` reads it backwards
    to say which field of a draft a problem reported against it came from.

    Args:
        number: The question's number, from 1.
        title: The question's title, quoted even where it is empty.
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
        compile: Whether to also compile the set as Lambda Feedback's PDF generator
            will, which needs pandoc and xelatex - see
            :mod:`in2lambda.validation.pdf`.

    Returns:
        One :class:`~in2lambda.api.problem.Problem` per problem found, each naming the
        question, part and field to look at, in the order they are written - save for
        what KaTeX refused, which comes last because the whole set is rendered at once.
        An empty list means nothing was found - not that the set will import, since
        only some mistakes can be seen from here.

    Examples:
        >>> from in2lambda.api.set import Set
        >>> from in2lambda.validation import validate
        >>> s = Set()
        >>> s.add_question("Angles", "Turn through $90^\\circ$.")
        >>> [str(problem) for problem in validate(s, compile=False)]
        ['Question 1 "Angles", main text: ^\\circ does not display; write the degree sign ° instead']
    """
    problems: list[Problem] = []
    # Every markdown field with the location to report it against, kept so that the
    # whole set can then be compiled in one go rather than a field at a time. The maths
    # is collected the same way, and rendered in one Node process.
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
                # An answer box is only in the PDF if it is marked to be, so LaTeX it
                # would not compile cannot break one unless it is.
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

    The question is needed because an image reference is only good if that image is
    among the question's, and so will be written into the export's ``media/``.

    The field's maths is appended to `expressions` rather than rendered here, so that
    the whole set takes one Node process instead of one per field.
    """
    problems: list[Problem] = []

    delimiters = math_delimiter_checker(markdown)
    if delimiters is not MathDelimiterError.PASSED:
        problems.append(Problem(location, delimiters.value))

    # The writer rewrites a reference to the name of the image it matches, and carries
    # that image into media/; one it matches nothing for is left as written, which is
    # exactly the reference Lambda Feedback will not find.
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

    Expressions the lists have nothing to say about are appended to `expressions` for
    KaTeX itself to render. The ones they do object to are not: their message says what
    to write instead, where KaTeX's only says what it choked on, and one fault reads
    better as one line.
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
        # Where the field's delimiters are wrong, what is between them is not reliably
        # the expression the author meant, so it is not rendered. The checks above are
        # reported against the field rather than a character range, so they still run.
        if not unsupported and delimiters is MathDelimiterError.PASSED:
            expressions.append(
                _Expression(location, span.start() + 1, span.end(), maths, display)
            )

    return problems


def _katex_rejections(expressions: list[_Expression]) -> list[Problem]:
    """What KaTeX itself refuses to render, the whole set in one Node process.

    Node is optional: someone authoring questions in Python should not have to install
    it, so without it this one check is skipped and says what to install instead.
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
            # combining low lines, so its messages are never ASCII, and Node writes
            # them as UTF-8 whatever LANG says.
            encoding="utf-8",
            check=True,
        )
        rejections = json.loads(rendered.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        # Anything named node on the PATH is run here, and it may not be Node.js at all.
        # Validation reports, never refuses, so a check that cannot be run says so and
        # leaves the rest of the report - and the export - alone.
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
    """Where node is, or None if it is not installed."""
    return shutil.which("node")


@cache
def _katex_lacks() -> dict[str, str | None]:
    """What KaTeX lacks, keyed by the command as it is written rather than as a regex.

    :func:`~in2lambda.katex_convert.katex_convert.unsupported_commands` gives the lists
    as they are written, where a command's backslash is escaped for the replacing pass.
    The entries that are not a single command, such as whole environments, simply never
    match one.
    """
    return {
        pattern.replace("\\\\", "\\"): (
            replacement.replace("\\\\", "\\") if replacement else replacement
        )
        for pattern, replacement in unsupported_commands().items()
    }


def _area_problems(area: ResponseArea) -> list[str]:
    """Where an answer box's answer does not fit the box, or what marks it.

    Only the three response type / evaluation function pairings the real exports use
    (``tests/fixtures/exports/README.md``) are judged. Any other evaluation function
    may expect an answer of any shape, and guessing at it would only cry wolf.
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
