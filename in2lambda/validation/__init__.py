"""Checks a question set for what Lambda Feedback would refuse or render wrongly.

A question can be perfectly valid JSON and still fail to import, or import and then
look wrong: an answer that does not fit the box marking it, an image the export will
not contain, maths KaTeX cannot render. Authors otherwise find this out by uploading
and looking.

Everything here reports, never refuses: :func:`validate` returns what it found and the
export goes ahead regardless, since a problem may well be deliberate.
"""

import re
from functools import cache
from pathlib import Path

from in2lambda.api.problem import Problem
from in2lambda.api.question import Question
from in2lambda.api.response_area import ResponseArea
from in2lambda.api.set import Set
from in2lambda.katex_convert.katex_convert import unsupported_commands
from in2lambda.validation import pdf
from in2lambda.validation.delimiters import MathDelimiterError, math_delimiter_checker

__all__ = ["MathDelimiterError", "Problem", "math_delimiter_checker", "validate"]

_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
"""A markdown image, e.g. ``![pictureTag](question_000_Title_0001.png)``."""

_MATHS = re.compile(r"(?<!\\)\$\$(.*?)(?<!\\)\$\$|(?<!\\)\$(.*?)(?<!\\)\$", re.DOTALL)
"""Display maths first, so that ``$$ ... $$`` is not read as two empty ``$ ... $``."""

_COMMAND = re.compile(r"\\[a-zA-Z]+")

_DEGREES = re.compile(r"\^\s*\{?\s*\\circ")
"""``^\\circ``, with or without braces around it."""


def validate(question_set: Set, compile: bool = True) -> list[Problem]:
    r"""Everything in2lambda can tell is wrong with a set, in the order it is written.

    Args:
        question_set: The set about to be exported.
        compile: Whether to also compile the set as Lambda Feedback's PDF generator
            will, which needs pandoc and xelatex - see
            :mod:`in2lambda.validation.pdf`.

    Returns:
        One :class:`~in2lambda.api.problem.Problem` per problem found, each naming the
        question, part and field to look at. An empty list means nothing was found -
        not that the set will import, since only some mistakes can be seen from here.

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
    # whole set can then be compiled in one go rather than a field at a time.
    fields: list[tuple[str, str]] = []
    images: list[str] = []

    def check(
        markdown: str, question: Question, location: str, compiled: bool = True
    ) -> list[Problem]:
        if compiled:
            fields.append((location, markdown))
        return _markdown_problems(markdown, question, location)

    for number, question in enumerate(question_set.questions, start=1):
        where = f'Question {number} "{question.title}"'
        problems += check(question.main_text, question, f"{where}, main text")

        images += question.images
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
                problems += check(markdown, question, f"{part_where}, {field}")

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

    return problems


def _markdown_problems(
    markdown: str, question: Question, location: str
) -> list[Problem]:
    """Every problem in one markdown field, reported against `location`.

    The question is needed because an image reference is only good if that image is
    among the question's, and so will be written into the export's ``media/``.
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

    problems += _katex_problems(markdown, location)
    return problems


def _katex_problems(markdown: str, location: str) -> list[Problem]:
    """Maths that KaTeX, which Lambda Feedback renders with, will not display."""
    problems: list[Problem] = []
    lacks = _katex_lacks()

    for span in _MATHS.finditer(markdown):
        maths = span[1] if span[1] is not None else span[2]
        for command in _COMMAND.findall(maths):
            if command in lacks:
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

    return problems


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
