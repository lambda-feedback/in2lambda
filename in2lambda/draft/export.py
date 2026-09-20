"""Turns a finished draft into the set it describes, to upload or to look at.

A draft is a map of fields - ``q1.text``, ``q1.p2.text``, ``q1.solution`` - and an
export is a :class:`~in2lambda.api.set.Set` of questions holding parts. :func:`as_set`
is the one place that reads the one as the other, so both what is written out and what
is rendered for review come from the same reading of the draft.

:func:`build` refuses a draft the checks have not looked at, or have something to say
about. There is no timestamp in that: every command that changes a draft takes its
report with it, so a draft holding one has been checked since it last changed, and
`in2lambda.source.frozen` refuses one whose source has moved on underneath it.
:func:`render` is gated on nothing, since looking at a draft is how what the checks
found gets fixed.
"""

import re
import warnings
from pathlib import Path
from typing import Any

from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.set import Set
from in2lambda.json_convert.json_convert import _question_stem, _question_title
from in2lambda.source import DRAFT, ConversionToolsMissing, SourceError, frozen
from in2lambda.validation import _IMAGE, _location, pdf

_QUESTION = re.compile(r"q(\d+)\.text")
"""A question's text, and the number that orders it."""

_PART = re.compile(r"q(\d+)\.p(\d+)\.text")
"""A part's text, and the question and part numbers that order it."""


class NotValidated(SourceError):
    """A draft is being exported that the checks have not passed, or not seen at all."""


class MissingImage(SourceError):
    """A field refers to an image file that is not beside the draft.

    The checks do not look at files, so such a draft validates clean; it is refused
    here rather than exported, since what would be uploaded is a question with a broken
    figure in it.
    """


def as_set(draft: dict[str, Any], directory: str = ".") -> Set:
    r"""The set a draft's fields describe, in question and part order.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.
        directory: Where the draft is, and so what the images it names are beside.

    Returns:
        One question per ``qN.text``, holding one part per ``qN.pM.text`` with the
        worked solution written for it. A question's own ``qN.solution`` answers every
        part that has none of its own; where every part has one already, or the
        question was written without parts, it becomes a part of its own holding
        nothing but that solution. That is the rule
        :meth:`~in2lambda.api.question.Question.add_solution` applies, so a draft
        exports as the same sheet converted by `in2lambda convert` does. A question
        written with neither parts nor a solution holds one part with nothing in it,
        which is the question as the draft has it. A block marked ignore is in no
        question: it is the source's, not the set's.

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
            # answers each part it does not answer separately. Where nothing is left for
            # it to answer it is a part of its own, as `add_solution` makes it one: a
            # solution written beside a solution for every part is still the author's
            # wording, and dropping it would export less than the draft holds.
            if all(part_of.worked_solution for part_of in question.parts):
                question.parts.append(Part(worked_solution=fields[written]["value"]))
            else:
                for part_of in question.parts:
                    if not part_of.worked_solution:
                        part_of.worked_solution = fields[written]["value"]
        if not question.parts:
            # A question whose parts are yet to be written is still exported, and an
            # empty part is what it holds: `json_convert` leaves a question with no
            # parts at all carrying the template's own placeholder wording, which is
            # wording no field of the draft holds.
            question.parts.append(Part())
        # As the export refers to them: beside the draft, since that is where a command
        # naming a file names one. Whether the file is there is `build`'s question, not
        # asked here, so that a draft can be rendered while its figures are being found.
        for _, markdown in _fields(question, number):
            question.images += [
                str(Path(directory) / reference)
                for reference in _IMAGE.findall(markdown)
            ]
    return question_set


def located(draft: dict[str, Any]) -> dict[str, str]:
    """Which field of a draft each place `in2lambda.validation` reports against is.

    :func:`as_set` read backwards. The validator names a question, a part and a field
    of the export, which is no address in the draft that wrote it, so this walks the
    fields the way :func:`as_set` walks them and must be changed with it.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.

    Returns:
        The draft's field key for each location of the set it describes, the question's
        own location included - where a problem about the whole question, such as an
        image the export would not contain, is reported. A part answered by its
        question's solution is located at that solution, since that is the field to go
        and edit. Places no field of the draft wrote - a part's answer, the empty part
        a question written without any exports as - are not here: nothing is in them
        for the validator to find.

    Examples:
        >>> from in2lambda.draft.export import located
        >>> fields = {"q1.text": {"value": "State it."}, "q1.solution": {"value": "$x$"}}
        >>> located({"fields": fields})
        {'Question 1 ""': 'q1.text', 'Question 1 "", main text': 'q1.text', 'Question 1 "", part (a), worked solution': 'q1.solution'}
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
            if written in fields:
                where[_location(number, "", index, "worked solution")] = written
            elif solution in fields:
                where[_location(number, "", index, "worked solution")] = solution
        if solution in fields and all(
            f"q{number}.p{part}.solution" in fields for part in parts
        ):
            # The part `as_set` appends for a question's solution with no part left for
            # it to answer, which is the last one and holds nothing else.
            where[_location(number, "", len(parts), "worked solution")] = solution
    return where


def build(directory: str = ".", output_dir: str = "out") -> Path:
    """Writes the draft in a directory out as a Lambda Feedback set, if it is clean.

    Args:
        directory: Where the ``draft.json`` to export is.
        output_dir: Where to write the set's folder and its zip.

    Returns:
        The zip that was written, which is what Lambda Feedback imports.

    Raises:
        NotValidated: the draft has not been checked since it last changed, or the
            checks found something. Either way what would be uploaded is not what
            anybody has looked at.
        MissingImage: a field refers to an image file that is not beside the draft.
        SourceError: the draft is missing, is not one of ours, or was written from
            markdown that has changed since.
    """
    draft, _ = frozen(directory)
    if "report" not in draft:
        raise NotValidated(
            f"{DRAFT} has not been validated since it last changed, so what it would "
            "export is what nothing has checked. Run in2lambda validate."
        )
    if draft["report"]:
        raise NotValidated(
            "\n".join(finding["message"] for finding in draft["report"])
            + f"\n{DRAFT} is not exported while its report says this. Fix what it "
            "names, or mark the blocks it is about as ignored, and run in2lambda "
            "validate again."
        )
    exported = as_set(draft, directory)
    # The export carries every image a field refers to into media/, which is the only
    # place Lambda Feedback looks for one, so a file that is not there is not something
    # to write the set without: `json_convert` would raise a bare FileNotFoundError over
    # it. The checks read the draft and not the folder it is in, so a draft they found
    # nothing in can still say this.
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


def render(directory: str = ".", output_dir: str = "out") -> list[Path]:
    """Writes each question of the draft in a directory as a PDF, for review.

    The questions are compiled as Lambda Feedback's own PDF generator compiles them,
    under a heading naming each, so what comes out is what a student would be shown.
    The checks are not run first: looking at a draft is how what they found gets fixed.
    Nor does a figure that is not beside the draft stop a question being looked at -
    the compiler drops the reference and typesets the rest of it - or a question the
    compiler gives up on altogether stop the rest of the draft being written out.

    Args:
        directory: Where the ``draft.json`` to render is.
        output_dir: Where to write the PDFs, named as the export names its questions.

    Returns:
        The PDF written for each question that was rendered, in question order.

    Raises:
        ConversionToolsMissing: pandoc or xelatex is not installed.
        CompileFailed: no question could be rendered at all, so there is nothing to
            look at.
        SourceError: the draft is missing, is not one of ours, or was written from
            markdown that has changed since.

    Warns:
        UserWarning: once per LaTeX error in a question that was rendered anyway, and
            once for a question the compiler gave up on while others rendered.
    """
    if missing := pdf.missing_tools():
        raise ConversionToolsMissing(
            f"Rendering questions needs {' and '.join(missing)}."
        )
    draft, _ = frozen(directory)

    written = []
    refused = []
    for index, question in enumerate(as_set(draft, directory).questions):
        stem = _question_stem(index, _question_title(question, index))
        output = Path(output_dir) / f"{stem}.pdf"
        # Headed with the question's number, so that a stack of these can be read
        # through, and so that a question with nothing written in it is still a page.
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
        # Nothing at all to look at, which is a failed run rather than a fault in one
        # question of it, so it is said the way a draft that cannot be read is.
        raise pdf.CompileFailed("; ".join(refused))
    for failure in refused:
        # One question TeX cannot finish is a fault in that question like any other, and
        # the ones that do compile are still what the draft is being rendered for.
        warnings.warn(failure, stacklevel=2)
    return written


def _fields(question: Question, number: int) -> list[tuple[str, str]]:
    """Every markdown field of a question, each with where to report an error in it.

    Named as `in2lambda.validation` names them, save for the title, since a draft
    writes none: the renderer marks the document with these, so what it reports back
    reads the same as what the validator reports.
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
