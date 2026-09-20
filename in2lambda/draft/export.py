"""Turns a finished draft into the set it describes, to upload or to read.

A draft is a map of fields - ``q1.text``, ``q1.p2.text``, ``q1.solution`` - and an export
is a :class:`~in2lambda.api.set.Set` of questions holding parts. :func:`as_set` is the one
function that reads a draft as a set, so the set written out and the set rendered for
review come from one reading of the draft.

:func:`build` refuses a draft the checks have not read, or have found an error in. A
finding at level warning - a question or part nothing answers - is printed, and
:func:`build` writes the set, because a sheet whose solutions are in another file is
still a sheet. No timestamp records the check: every command that changes a draft deletes
its report, so a draft holding a report has been checked since it last changed, and
`in2lambda.source.frozen` refuses a draft whose source has changed since. :func:`render`
runs whether or not the report holds findings, because reading a draft is how an author
fixes what the checks found.
"""

import re
import warnings
from pathlib import Path
from typing import Any

from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.set import Set
from in2lambda.json_convert.json_convert import _IMAGE, _question_stem, _question_title
from in2lambda.source import ConversionToolsMissing, SourceError, frozen
from in2lambda.validation import _location, pdf

_QUESTION = re.compile(r"q(\d+)\.text")
"""A question's text, and the number that orders it."""

_PART = re.compile(r"q(\d+)\.p(\d+)\.text")
"""A part's text, and the question and part numbers that order it."""


class NotValidated(SourceError):
    """A draft being exported has not passed the checks, or has not been checked."""


class MissingImage(SourceError):
    """A field refers to an image file that is not beside the draft.

    The checks read the draft and not the folder holding it, so such a draft passes them.
    :func:`build` refuses the draft, because the set would upload a question holding a
    broken figure.
    """


def as_set(draft: dict[str, Any], directory: str = ".") -> Set:
    r"""The set a draft's fields describe, in question and part order.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.
        directory: Where the draft is, and so where the images it names sit.

    Returns:
        One question per ``qN.text``, holding one part per ``qN.pM.text`` with the worked
        solution written for it. A question's own ``qN.solution`` answers every part that
        has no solution of its own. Where every part has one already, or the question was
        written without parts, ``qN.solution`` becomes a part of its own holding that
        solution. :meth:`~in2lambda.api.question.Question.add_solution` applies the same
        rule, so a draft exports as the same sheet converted by `in2lambda convert` does.
        A question written with neither parts nor a solution holds one empty part, which
        is the question as the draft holds it. A block marked ignore is in no question,
        because it belongs to the source and not to the set.

    Examples:
        >>> from in2lambda.draft.export import as_set
        >>> fields = {
        ...     "q1.text": {"value": "Water flows through a pipe."},
        ...     "q1.p1.text": {"value": "State the continuity equation."},
        ...     "q1.solution": {"value": "$Q = \\pi d^2 v / 4$."},
        ...     "b1.ignore": {"value": True},
        ... }
        >>> as_set({"fields": fields}).questions
        [Question(title='', parts=[Part(text='State the continuity equation.', worked_solution='$Q = \\pi d^2 v / 4$.', answer='', response_areas=[])], images=[], main_text='Water flows through a pipe.')]
    """
    fields = draft["fields"]
    question_set = Set()
    for number in sorted(
        int(found[1]) for key in fields if (found := _QUESTION.fullmatch(key))
    ):
        question_set.add_question(main_text=fields[f"q{number}.text"]["value"])
        question = question_set.questions[-1]
        for part in sorted(
            int(found[2])
            for key in fields
            if (found := _PART.fullmatch(key)) and int(found[1]) == number
        ):
            question.add_part_text(fields[f"q{number}.p{part}.text"]["value"])
            if (written := f"q{number}.p{part}.solution") in fields:
                question.parts[-1].worked_solution = fields[written]["value"]
        if (written := f"q{number}.solution") in fields:
            # A sheet often writes one worked solution for a whole question, which
            # answers each part that has no solution of its own. Where no part is left to
            # answer, the solution becomes a part of its own, as `add_solution` makes it
            # one: the wording is the author's, and dropping it would export less than
            # the draft holds.
            if all(part_of.worked_solution for part_of in question.parts):
                question.parts.append(Part(worked_solution=fields[written]["value"]))
            else:
                for part_of in question.parts:
                    if not part_of.worked_solution:
                        part_of.worked_solution = fields[written]["value"]
        if not question.parts:
            # A question whose parts are not yet written is exported with one empty part,
            # because `json_convert` leaves a question holding no parts with the
            # template's own placeholder wording, which no field of the draft wrote.
            question.parts.append(Part())
        # The paths are read as the export writes them, beside the draft, because a
        # command names a file from the draft's directory. `build` checks that each file
        # is there, and this function does not, so that a draft renders while its figures
        # are still being found.
        for _, markdown in _fields(question, number):
            question.images += [
                str(Path(directory) / reference)
                for reference in _IMAGE.findall(markdown)
            ]
    return question_set


def located(draft: dict[str, Any]) -> dict[str, str]:
    """The field of a draft each place `in2lambda.validation` reports against.

    :func:`located` reads :func:`as_set` backwards. The validator names a question, a
    part and a field of the export, which name no field of the draft that wrote them, so
    this function walks the fields as :func:`as_set` walks them, and changes with it.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.

    Returns:
        The draft's field key for each location of the set it describes, the question's
        own location included, where a problem about the whole question is reported, such
        as an image the export would not contain. A part answered by its question's
        solution is located at that solution, which is the field to edit. Places no field
        of the draft wrote - a part's answer, the empty part a question written without
        parts exports as - are left out, because the validator finds nothing in them.

    Examples:
        >>> from in2lambda.draft.export import located
        >>> fields = {"q1.text": {"value": "State it."}, "q1.solution": {"value": "$x$"}}
        >>> located({"fields": fields})
        {'Question 1 ""': 'q1.text', 'Question 1 "", main text': 'q1.text', 'Question 1 "", part (a), worked solution': 'q1.solution'}
        >>> fields["q1.p1.text"] = {"value": "Do it."}
        >>> fields["q1.p1.solution"] = {"value": ""}
        >>> located({"fields": fields})['Question 1 "", part (a), worked solution']
        'q1.solution'
    """
    fields = draft["fields"]
    where = {}
    for number in sorted(
        int(found[1]) for key in fields if (found := _QUESTION.fullmatch(key))
    ):
        where[_location(number, "")] = f"q{number}.text"
        where[_location(number, "", field="main text")] = f"q{number}.text"
        parts = sorted(
            int(found[2])
            for key in fields
            if (found := _PART.fullmatch(key)) and int(found[1]) == number
        )
        solution = f"q{number}.solution"
        for index, part in enumerate(parts):
            where[_location(number, "", index, "text")] = f"q{number}.p{part}.text"
            written = f"q{number}.p{part}.solution"
            # On the value and not the key, as `as_set` reads it: a solution field
            # written empty leaves the part for its question's solution to answer.
            if fields.get(written, {}).get("value"):
                where[_location(number, "", index, "worked solution")] = written
            elif solution in fields:
                where[_location(number, "", index, "worked solution")] = solution
        if solution in fields and all(
            fields.get(f"q{number}.p{part}.solution", {}).get("value") for part in parts
        ):
            # The part `as_set` appends for a question's solution when no part is left to
            # answer, which is the last part and holds nothing else.
            where[_location(number, "", len(parts), "worked solution")] = solution
    return where


def build(draft: str | Path, output_dir: str = "out") -> Path:
    """Writes a draft out as a Lambda Feedback set, where the checks found no error.

    Args:
        draft: The path of the draft to export.
        output_dir: Where to write the set's folder and its zip.

    Returns:
        The zip that was written, which Lambda Feedback imports.

    Raises:
        NotValidated: the draft has not been checked since it last changed, or the checks
            found an error in it. The set would then hold what nobody has read.
        MissingImage: a field refers to an image file that is not beside the draft.
        SourceError: the draft is missing, is not a draft in2lambda wrote, or was written
            from markdown that has changed since.

    Warns:
        UserWarning: once per finding the checks made at level warning, which is a
            question or part the draft holds no solution for. The set is written all the
            same.
    """
    # Imported here and not at the top of the module: `report` checks the set this
    # function writes, so `report` imports this module, and only this function reads a
    # report back.
    from in2lambda.draft.report import errors

    path = Path(draft)
    found, _ = frozen(path)
    if "report" not in found:
        raise NotValidated(
            f"{path.name} has not been validated since it last changed, so its export "
            "would hold what nothing has checked. Run in2lambda validate."
        )
    if refusing := errors(found["report"]):
        raise NotValidated(
            "\n".join(finding["message"] for finding in refusing)
            + f"\n{path.name} is not exported while its report holds these findings. Fix "
            "the fields they name, or mark the blocks they are about as ignored, and "
            "run in2lambda validate again."
        )
    for finding in found["report"]:
        # Printed and not refused: a sheet whose solutions are in another file, or
        # absent, is exported as it stands, and writing a solution in would put wording
        # in the set that no source holds.
        warnings.warn(finding["message"], stacklevel=2)
    exported = as_set(found, str(path.parent))
    # The export copies every image a field refers to into media/, which is the only
    # place Lambda Feedback reads an image from, and `json_convert` raises a bare
    # FileNotFoundError over a file that is not there. The checks read the draft and not
    # the folder holding it, so a draft they passed can still reach this.
    for number, question in enumerate(exported.questions, start=1):
        for image in question.images:
            if not Path(image).is_file():
                raise MissingImage(
                    f"Question {number} refers to an image, and there is no file at "
                    f"{image}. Put the image there, or take the reference out of the "
                    "field with in2lambda draft field replace."
                )
    exported.to_json(output_dir)
    return Path(output_dir) / "set.zip"


def render(draft: str | Path, output_dir: str = "out") -> list[Path]:
    """Writes each question of a draft as a PDF, for review.

    The questions are compiled as Lambda Feedback's own PDF generator compiles them,
    under a heading naming each question, so that the PDF shows what a student is shown.
    :func:`render` does not run the checks first, because reading a draft is how an
    author fixes what the checks found. A figure that is not beside the draft does not
    stop a question being rendered - the compiler drops the reference and typesets the
    rest - and a question the compiler gives up on does not stop the rest of the draft
    being written.

    Args:
        draft: The path of the draft to render.
        output_dir: Where to write the PDFs, named as the export names its questions.

    Returns:
        The PDF written for each question that was rendered, in question order.

    Raises:
        ConversionToolsMissing: pandoc or xelatex is not installed.
        CompileFailed: no question rendered, so there is no PDF to read.
        SourceError: the draft is missing, is not a draft in2lambda wrote, or was written
            from markdown that has changed since.

    Warns:
        UserWarning: once per LaTeX error in a question that was rendered anyway, and
            once for a question the compiler gave up on while others rendered.
    """
    if missing := pdf.missing_tools():
        raise ConversionToolsMissing(
            f"Rendering questions needs {' and '.join(missing)}."
        )
    path = Path(draft)
    found, _ = frozen(path)

    written = []
    refused = []
    for index, question in enumerate(as_set(found, str(path.parent)).questions):
        stem = _question_stem(index, _question_title(question, index))
        output = Path(output_dir) / f"{stem}.pdf"
        # Headed with the question's number, so that a stack of PDFs reads in order and
        # a question with nothing written in it is still a page.
        heading = f"Question {index + 1}"
        fields = [(heading, f"# {heading}")] + _fields(question, index + 1)
        try:
            problems = pdf.render(fields, question.images, output)
        except pdf.CompileFailed as failed:
            refused.append(str(failed))
            continue
        for problem in problems:
            warnings.warn(str(problem), stacklevel=2)
        written.append(output)
    if refused and not written:
        # No PDF to read, which is a failed run and not a fault in one question, so
        # `render` raises as it does for a draft it cannot read.
        raise pdf.CompileFailed("; ".join(refused))
    for failure in refused:
        # One question TeX cannot finish is a fault in that question, and the questions
        # that do compile are what the author asked to read.
        warnings.warn(failure, stacklevel=2)
    return written


def _fields(question: Question, number: int) -> list[tuple[str, str]]:
    """Every markdown field of a question, each with where to report an error in it.

    The names are `in2lambda.validation`'s, except for the title, which no draft writes.
    The renderer marks the document with these names, so that it reports an error in the
    words the validator reports one in.
    """
    where = f"Question {number}"
    fields = [(f"{where}, main text", question.main_text)]
    for index, part in enumerate(question.parts):
        part_where = f"{where}, part ({chr(ord('a') + index)})"
        fields += [
            (f"{part_where}, text", part.text),
            (f"{part_where}, worked solution", part.worked_solution),
        ]
    return fields
