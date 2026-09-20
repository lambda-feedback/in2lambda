"""Checks a question set for what Lambda Feedback would refuse or render wrongly.

A question can be perfectly valid JSON and still fail to import, or import and then
look wrong: an answer that does not fit the box marking it, an image the export will
not contain, maths KaTeX cannot render. Authors otherwise find this out by uploading
and looking.

Everything here reports, never refuses: :func:`validate` returns what it found and the
export goes ahead regardless, since a problem may well be deliberate.

Maths is rendered with KaTeX itself, which needs Node.js. That is the one check with a
dependency outside Python: without Node it is skipped with a warning saying so.
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
from in2lambda.katex_convert.katex_convert import unsupported_commands
from in2lambda.validation.delimiters import MathDelimiterError, math_delimiter_checker

__all__ = ["MathDelimiterError", "Problem", "math_delimiter_checker", "validate"]

_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
"""A markdown image, e.g. ``![pictureTag](question_000_Title_0001.png)``."""

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


def validate(question_set: Set) -> list[Problem]:
    r"""Everything in2lambda can tell is wrong with a set, in the order it is written.

    Args:
        question_set: The set about to be exported.

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
        >>> [str(problem) for problem in validate(s)]
        ['Question 1 "Angles", main text: ^\\circ does not display; write the degree sign ° instead']
    """
    problems: list[Problem] = []
    expressions: list[_Expression] = []

    for number, question in enumerate(question_set.questions, start=1):
        where = f'Question {number} "{question.title}"'
        problems += _markdown_problems(
            question.main_text, question, f"{where}, main text", expressions
        )

        for image in question.images:
            if not Path(image).is_file():
                problems.append(Problem(where, f"there is no image file at {image}"))

        for index, part in enumerate(question.parts):
            part_where = f"{where}, part ({chr(ord('a') + index)})"
            for field, markdown in (
                ("text", part.text),
                ("worked solution", part.worked_solution),
                ("answer", part.answer),
            ):
                problems += _markdown_problems(
                    markdown, question, f"{part_where}, {field}", expressions
                )

            for area_number, area in enumerate(part.response_areas, start=1):
                area_where = f"{part_where}, answer box {area_number}"
                problems += [
                    Problem(area_where, message) for message in _area_problems(area)
                ]
                for field, markdown in (
                    ("pre_text", area.pre_text),
                    ("post_text", area.post_text),
                    ("content_after", area.content_after),
                ):
                    problems += _markdown_problems(
                        markdown, question, f"{area_where}, {field}", expressions
                    )
                options = (area.config or {}).get("options")
                if isinstance(options, list):
                    for option_number, option in enumerate(options, start=1):
                        problems += _markdown_problems(
                            option,
                            question,
                            f"{area_where}, option {option_number}",
                            expressions,
                        )

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

    # Lambda Feedback finds an image in media/ by its file name alone.
    media = {Path(image).name for image in question.images}
    for reference in _IMAGE.findall(markdown):
        if Path(reference).name not in media:
            problems.append(
                Problem(location, f"the export will not contain the image {reference}")
            )

    # Where the delimiters are wrong the expressions cannot be picked out reliably, and
    # the field has its report already, so its maths is left where it is.
    if delimiters is MathDelimiterError.PASSED:
        problems += _katex_problems(markdown, location, expressions)
    return problems


def _katex_problems(
    markdown: str, location: str, expressions: list[_Expression]
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
        if not unsupported:
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

    rendered = subprocess.run(
        [node, str(_CHECK)],
        input=json.dumps(
            [
                {"tex": expression.tex, "display": expression.display}
                for expression in expressions
            ]
        ),
        capture_output=True,
        text=True,
        check=True,
    )
    problems: list[Problem] = []
    for rejection in json.loads(rendered.stdout):
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
