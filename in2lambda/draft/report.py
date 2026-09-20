"""Checks a draft as a whole, and writes what the checks find into the draft.

A draft is written one command at a time, and no one command sees the faults a run of them
leaves: a block nobody quoted, two fields taken from the same lines, a question numbered 3
where there is no 2, a part nothing answers. So the checks read the finished draft and
write what they find into it as its ``report``, which the agent or the person writing the
draft reads for the faults to fix, without reading the draft itself.

The checks report and never refuse, because the author may have intended what a check
found. The checks themselves read only the draft - its blocks, its field keys, their
ranges and their values. `in2lambda.validation` reads the text of a question:
:func:`problems` exports the set the draft describes and checks that set, so that maths
Lambda Feedback will not render is reported against the field holding it, before the set
is uploaded.

Each finding records the level it was found at, which `in2lambda.draft.export` reads. An
error is the draft contradicting its own source or its own export: lines no field
accounts for, two fields quoting the same lines, a hole in the numbering, a field holding
nothing, maths that will not render. No sheet is written that way. A warning is a finding
the author may have intended: many sheets write their solutions in another file, or write
none, so in2lambda reports a question nothing answers to the person building the set and
writes the set.
"""

import re
import warnings
from pathlib import Path
from typing import Any

from in2lambda.draft.export import as_set, located
from in2lambda.source import frozen, save
from in2lambda.validation import pdf

Finding = dict[str, Any]
"""One thing a check found: ``{"check", "level", "field", "ranges", "message"}``.

``check`` names the check that found it, and is ``problem`` where `in2lambda.validation`
found it over the set the draft describes. ``level`` is :data:`ERROR` or :data:`WARNING`.
``field`` is the block id or field key the finding is about. ``ranges`` are the lines, as
``[[start, end], ...]``. ``message`` is a sentence naming all of those, so that one line
of the report can be acted on by itself.
"""

ERROR = "error"
"""A finding that stops an export: the draft holds wording no source of it holds."""

WARNING = "warning"
"""A finding the export prints before writing the set, because the sheet may be right."""

_NUMBERED = re.compile(r"((?:q\d+\.p)|q)(\d+)\.text")
"""A question's or a part's text, split into what numbers it and the number."""

_PART = re.compile(r"(q\d+)\.p\d+\.text")
"""A part's text, and the question it belongs to."""

_QUESTION = re.compile(r"(q\d+)\.text")
"""A question's text, and the question it is."""

_UNPLACED = float("inf")
"""Where a finding about no particular line sorts: after every finding about one."""


def overlapping(ranges: list[list[int]], other: list[list[int]]) -> bool:
    """Whether any line falls in both sets of line ranges.

    Args:
        ranges: Line ranges, as ``[[start, end], ...]``, each end inclusive.
        other: The ranges to test `ranges` against.

    Returns:
        Whether the two sets share a line.

    Examples:
        >>> from in2lambda.draft.report import overlapping
        >>> overlapping([[5, 6]], [[6, 8]])
        True
        >>> overlapping([[5, 6]], [[7, 8]])
        False
    """
    return any(
        taken[0] <= end and start <= taken[1]
        for taken in other
        for start, end in ranges
    )


def _where(ranges: list[list[int]]) -> str:
    """The lines a finding covers, as its message names them, or "" for no lines."""
    if not ranges:
        return ""
    return " (lines " + ", ".join(f"{start}-{end}" for start, end in ranges) + ")"


def _runs(lines: list[int]) -> list[list[int]]:
    """Line numbers in order, grouped into the ranges they run in."""
    runs: list[list[int]] = []
    for line in lines:
        if runs and runs[-1][1] == line - 1:
            runs[-1][1] = line
        else:
            runs.append([line, line])
    return runs


def uncovered(draft: dict[str, Any]) -> list[Finding]:
    """Blocks of the sources that no field, and no `mark ignore`, accounts for.

    A block quoted in part is reported for the rest of it: a question taken from the first
    line of a block leaves the other lines unaccounted for. This check accounts for a
    block by the lines the fields were taken from and not by the block's name, so that an
    ignore of a whole block covers both halves of a block `split block` has cut in two.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.

    Returns:
        One :data:`Finding` per block holding lines no field accounts for, in document
        order and source by source. `in2lambda.spec` reports through this function as
        well as the checks do, because a spec run asks the same question as it finishes.
    """
    # By source as well as by line: line 12 of the solutions document is not line 12 of
    # the sheet, so a field quoting one document accounts for no line of the other.
    claimed = {
        (field.get("source", 1), line)
        for field in draft["fields"].values()
        for start, end in field["ranges"]
        for line in range(start, end + 1)
    }
    found = []
    for number, source in enumerate(draft["sources"], start=1):
        for block in source["blocks"]:
            free = _runs(
                [
                    line
                    for line in range(block["start"], block["end"] + 1)
                    if (number, line) not in claimed
                ]
            )
            if free:
                found.append(
                    {
                        "check": "uncovered",
                        "level": ERROR,
                        "field": block["id"],
                        "ranges": free,
                        "message": f"{block['id']}{_where(free)} is in no field and not "
                        "marked ignore.",
                    }
                )
    return found


def _overlaps(draft: dict[str, Any]) -> list[Finding]:
    """Pairs of fields quoted from some of the same lines.

    No command writes such a pair, because `record` refuses the second field. This check
    reports a draft edited by hand, in which one of the two fields quotes the wrong lines.
    """
    fields = draft["fields"]
    keys = sorted(fields)
    return [
        {
            "check": "overlap",
            "level": ERROR,
            "field": key,
            "ranges": fields[key]["ranges"],
            "message": f"{key}{_where(fields[key]['ranges'])} and {other}"
            f"{_where(fields[other]['ranges'])} are taken from some of the same lines.",
        }
        for index, key in enumerate(keys)
        for other in keys[index + 1 :]
        # Of the same source, because the same line numbers in two documents are
        # different lines, as `in2lambda.draft.record` compares them.
        if fields[key].get("source", 1) == fields[other].get("source", 1)
        and overlapping(fields[key]["ranges"], fields[other]["ranges"])
    ]


def _gaps(draft: dict[str, Any]) -> list[Finding]:
    """Questions or parts numbered past a number that no command wrote.

    `in2lambda.draft._next` gives the numbers out and leaves no gap, so this check too
    reports a draft edited by hand: a question renumbered, or one deleted from the middle.
    """
    numbered: dict[str, list[int]] = {}
    for key in draft["fields"]:
        if named := _NUMBERED.fullmatch(key):
            numbered.setdefault(named[1], []).append(int(named[2]))
    return [
        {
            "check": "gap",
            "level": ERROR,
            "field": f"{prefix}{missing}.text",
            "ranges": [],
            "message": f"There is no {prefix}{missing}.text, though "
            f"{prefix}{max(numbers)}.text is written: the numbering skips it.",
        }
        for prefix, numbers in numbered.items()
        for missing in range(1, max(numbers))
        if missing not in numbers
    ]


def _without_solutions(draft: dict[str, Any]) -> list[Finding]:
    """Parts, and questions written without parts, that nothing in the draft answers.

    A part is answered by its own solution, or by the solution of the question it belongs
    to, because a sheet often writes one worked solution covering every part. A question
    with parts is answered through its parts and is not reported. A question without parts
    is reported where nothing answers it.
    """
    fields = draft["fields"]
    found = []
    for key in sorted(fields):
        if named := _PART.fullmatch(key):
            part = key.removesuffix(".text")
            if f"{part}.solution" in fields or f"{named[1]}.solution" in fields:
                continue
            found.append(
                {
                    "check": "no-solution",
                    "level": WARNING,
                    "field": part,
                    "ranges": fields[key]["ranges"],
                    "message": f"{part}{_where(fields[key]['ranges'])} has no solution: "
                    f"neither {part}.solution nor {named[1]}.solution is written.",
                }
            )
        elif named := _QUESTION.fullmatch(key):
            question = named[1]
            if f"{question}.solution" in fields or any(
                (belongs := _PART.fullmatch(other)) and belongs[1] == question
                for other in fields
            ):
                continue
            found.append(
                {
                    "check": "no-solution",
                    "level": WARNING,
                    "field": question,
                    "ranges": fields[key]["ranges"],
                    "message": f"{question}{_where(fields[key]['ranges'])} has no "
                    f"solution: {question}.solution is not written, and it has no parts.",
                }
            )
    return found


def _empty(draft: dict[str, Any]) -> list[Finding]:
    """Fields holding nothing, which quote the wrong lines or no lines at all."""
    return [
        {
            "check": "empty",
            "level": ERROR,
            "field": key,
            "ranges": field["ranges"],
            "message": f"{key}{_where(field['ranges'])} is empty.",
        }
        for key, field in sorted(draft["fields"].items())
        if isinstance(field["value"], str) and not field["value"].strip()
    ]


def checks(draft: dict[str, Any]) -> list[Finding]:
    """Everything the checks find wrong with a draft, in the order of the source.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.

    Returns:
        One :data:`Finding` per fault, earliest line first and then by the field each one
        is about, with the findings about no particular line last. An empty list means the
        draft covers its source once over, with no hole in its numbering. A list holding
        only warnings is a list `in2lambda.draft.export.build` prints and exports over.

    Examples:
        >>> from in2lambda.draft.report import checks
        >>> draft = {
        ...     "sources": [
        ...         {"blocks": [{"id": "b1", "type": "paragraph", "start": 1, "end": 2}]}
        ...     ],
        ...     "fields": {},
        ... }
        >>> [finding["message"] for finding in checks(draft)]
        ['b1 (lines 1-2) is in no field and not marked ignore.']
    """
    found = (
        uncovered(draft)
        + _overlaps(draft)
        + _gaps(draft)
        + _without_solutions(draft)
        + _empty(draft)
    )
    return sorted(found, key=_order)


def _order(finding: Finding) -> tuple[int | float, str]:
    """Where a finding sorts in a report: earliest line first, then by field."""
    return (
        finding["ranges"][0][0] if finding["ranges"] else _UNPLACED,
        finding["field"],
    )


def errors(findings: list[Finding]) -> list[Finding]:
    """The findings of a report that a draft cannot be exported over.

    Args:
        findings: A report, as :func:`checks` or :func:`validate` writes one.

    Returns:
        The findings at level :data:`ERROR`, in the order they were reported. The rest
        are warnings, which `in2lambda.draft.export.build` prints before writing the set.

    Examples:
        >>> from in2lambda.draft.report import errors
        >>> report = [{"level": "warning"}, {"level": "error", "check": "gap"}]
        >>> errors(report)
        [{'level': 'error', 'check': 'gap'}]
    """
    return [finding for finding in findings if finding["level"] == ERROR]


def problems(draft: dict[str, Any], directory: str = ".") -> list[Finding]:
    """What `in2lambda.validation` finds in the set the draft describes.

    :func:`problems` exports the draft as it stands and checks the set: maths delimiters,
    expressions KaTeX will not render, images the export would not carry, and the compile
    Lambda Feedback's PDF generator performs. A question that will not render is reported
    while the draft is being written, before the set is uploaded.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.
        directory: The directory the draft is in, which holds the images it names.

    Returns:
        One :data:`Finding` per problem, named by the field of the draft holding it and
        not by the question and part of the export, so that a line of the report can be
        acted on with `field replace`. A problem about no one field, such as the set
        failing to compile, keeps the validator's own name for where it is. Every finding
        is at level :data:`ERROR`, because Lambda Feedback will not render what they name.

    Warns:
        UserWarning: pandoc or xelatex is not installed, so the set was not compiled.
    """
    where = located(draft)
    if not where:
        # A draft holding no question describes an empty set, which holds no problem to
        # find and does not merit a xelatex run.
        return []

    missing = pdf.missing_tools()
    if missing:
        # As `_katex_rejections` does without Node.js: a check that cannot run names the
        # packages to install and leaves the rest of the report alone.
        warnings.warn(
            "The set the draft describes was not compiled as the PDF generator would: "
            "install " + " and ".join(missing),
            stacklevel=2,
        )

    fields = draft["fields"]
    found = []
    for problem in as_set(draft, directory).problems(compile=not missing):
        location = max(
            (named for named in where if problem.location.startswith(named)),
            key=len,
            default="",
        )
        if location:
            key = where[location]
            ranges = fields[key]["ranges"]
            # Whatever the location says past the field: KaTeX names the characters it
            # stopped at, and the field holds those characters.
            rest = problem.location[len(location) :]
            finding = {
                "check": "problem",
                "level": ERROR,
                "field": key,
                "ranges": ranges,
                "message": f"{key}{_where(ranges)}{rest}: {problem.message}",
            }
        else:
            finding = {
                "check": "problem",
                "level": ERROR,
                "field": "",
                "ranges": [],
                "message": str(problem),
            }
        if finding not in found:
            # A question's solution answers every part that has no solution of its own,
            # so one fault in that solution is found once per part. Each finding names
            # the same field, the same lines and the same wording, and a second line of
            # the report would send the author to a `field replace` with nothing left to
            # replace.
            found.append(finding)
    return found


def validate(draft: str | Path) -> list[Finding]:
    """Checks a draft and writes the report into it.

    The report replaces the report already there, and the next command that changes the
    draft deletes it, because the report describes the draft as it stood.

    Args:
        draft: The path of the draft to check.

    Returns:
        Every :data:`Finding` the checks and `in2lambda.validation` made, as written
        into the draft.

    Raises:
        DraftMissing: there is no draft at that path.
        DraftUnreadable: the file at that path is not a draft in2lambda wrote.
        SourceUnreadable: a markdown the draft names has moved, or is not text.
        DraftExists: a markdown has changed since the draft was written from it, so
            the lines the report names would not be the lines it was written about.

    Warns:
        UserWarning: a check could not be run here - see :func:`problems`.
    """
    path = Path(draft)
    found, _ = frozen(path)
    found["report"] = sorted(
        checks(found) + problems(found, str(path.parent)), key=_order
    )
    save(path, found)
    return found["report"]
