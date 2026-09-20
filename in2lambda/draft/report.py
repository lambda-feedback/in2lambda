"""Checks a draft over as a whole, and writes what it finds into it.

A draft is written one command at a time, and what a run of them left out is not
something any one command can see: a block nobody quoted, two fields taken from the same
lines, a question numbered 3 where there is no 2, a part with nothing answering it. So
the finished draft is looked over at once, and what the checks find is written into it as
its ``report``, which is what whoever is writing the draft - an agent or a person - reads
to find out what is left to do, without reading the draft itself.

Everything here reports, never refuses: what the checks found may well be deliberate, and
deciding that is whoever is writing the draft's to do. The checks themselves read only
what is in the draft - its blocks, its field keys, their ranges and their values - and
what the text of a question says is `in2lambda.validation`'s: the set the draft describes
is exported and checked over as well, so that maths Lambda Feedback will not render is
reported against the field it is written in rather than found after uploading.
"""

import re
import warnings
from pathlib import Path
from typing import Any

from in2lambda.draft.export import as_set, located
from in2lambda.source import DRAFT, frozen, save
from in2lambda.validation import pdf

Finding = dict[str, Any]
"""One thing a check found: ``{"check", "field", "ranges", "message"}``.

``check`` is which check found it - ``problem`` where it was `in2lambda.validation`,
over the set the draft describes - ``field`` the block id or field key it is about,
``ranges`` the lines in question as ``[[start, end], ...]``, and ``message`` a sentence
naming all of that, so that a line of the report can be acted on by itself.
"""

_NUMBERED = re.compile(r"((?:q\d+\.p)|q)(\d+)\.text")
"""A question's or a part's text, split into what numbers it and the number."""

_PART = re.compile(r"(q\d+)\.p\d+\.text")
"""A part's text, and the question it belongs to."""

_UNPLACED = float("inf")
"""Where a finding about no particular line sorts: after every finding about one."""


def overlapping(ranges: list[list[int]], other: list[list[int]]) -> bool:
    """Whether any line falls in both sets of line ranges.

    Args:
        ranges: Line ranges, as ``[[start, end], ...]``, each end inclusive.
        other: The ranges to test them against.

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
    """The lines something covers, as a message names them, or "" if it covers none."""
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
    """Blocks of the source that no field, and no `mark ignore`, accounts for.

    A block partly quoted is reported for the rest of it: a question taken from the first
    line of a block leaves the other lines as much unaccounted for as a whole block would.
    Blocks are accounted for by the lines the fields were taken from rather than by name,
    so that a block `split block` has cut in two is covered by an ignore of the whole.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.

    Returns:
        One :data:`Finding` per block with lines nothing has made anything of, in
        document order. `in2lambda.spec` reports through this as well as the checks do:
        what a spec run left out is the same question asked the moment it finishes.
    """
    claimed = {
        line
        for field in draft["fields"].values()
        for start, end in field["ranges"]
        for line in range(start, end + 1)
    }
    found = []
    for block in draft["blocks"]:
        free = _runs(
            [
                line
                for line in range(block["start"], block["end"] + 1)
                if line not in claimed
            ]
        )
        if free:
            found.append(
                {
                    "check": "uncovered",
                    "field": block["id"],
                    "ranges": free,
                    "message": f"{block['id']}{_where(free)} is in no field and not "
                    "marked ignore.",
                }
            )
    return found


def _overlaps(draft: dict[str, Any]) -> list[Finding]:
    """Pairs of fields quoted from some of the same lines.

    No command writes such a pair - `record` refuses the second of them - so this is here
    for a draft edited by hand, where one of the two fields is quoting the wrong thing.
    """
    fields = draft["fields"]
    keys = sorted(fields)
    return [
        {
            "check": "overlap",
            "field": key,
            "ranges": fields[key]["ranges"],
            "message": f"{key}{_where(fields[key]['ranges'])} and {other}"
            f"{_where(fields[other]['ranges'])} are taken from some of the same lines.",
        }
        for index, key in enumerate(keys)
        for other in keys[index + 1 :]
        if overlapping(fields[key]["ranges"], fields[other]["ranges"])
    ]


def _gaps(draft: dict[str, Any]) -> list[Finding]:
    """Questions or parts numbered past one that was never written.

    Numbers are given out by `in2lambda.draft._next`, which leaves no gap, so this too is
    a draft that was edited: a question renumbered, or one deleted out of the middle.
    """
    numbered: dict[str, list[int]] = {}
    for key in draft["fields"]:
        if named := _NUMBERED.fullmatch(key):
            numbered.setdefault(named[1], []).append(int(named[2]))
    return [
        {
            "check": "gap",
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
    """Parts that nothing in the draft answers.

    A part is answered by its own solution or by the solution of the question it belongs
    to, since a sheet often writes one worked solution covering every part at once.
    """
    fields = draft["fields"]
    found = []
    for key in sorted(fields):
        if (named := _PART.fullmatch(key)) is None:
            continue
        part = key.removesuffix(".text")
        if f"{part}.solution" in fields or f"{named[1]}.solution" in fields:
            continue
        found.append(
            {
                "check": "no-solution",
                "field": part,
                "ranges": fields[key]["ranges"],
                "message": f"{part}{_where(fields[key]['ranges'])} has no solution: "
                f"neither {part}.solution nor {named[1]}.solution is written.",
            }
        )
    return found


def _empty(draft: dict[str, Any]) -> list[Finding]:
    """Fields holding nothing, which is a quotation of the wrong lines or of none."""
    return [
        {
            "check": "empty",
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
        One :data:`Finding` per thing found, earliest line first and then by what it is
        about, with the findings about no particular line last. An empty list means the
        draft covers its source once each, with nothing missing from its numbering.

    Examples:
        >>> from in2lambda.draft.report import checks
        >>> draft = {
        ...     "blocks": [{"id": "b1", "type": "paragraph", "start": 1, "end": 2}],
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
    """Where a finding goes in a report: earliest line first, then by what it is about."""
    return (
        finding["ranges"][0][0] if finding["ranges"] else _UNPLACED,
        finding["field"],
    )


def problems(draft: dict[str, Any], directory: str = ".") -> list[Finding]:
    """What `in2lambda.validation` finds in the set the draft describes.

    The draft is exported as it stands and the set checked over - maths delimiters,
    what KaTeX will not render, images the export would not carry, and the compile
    Lambda Feedback's PDF generator does - so that a question that will not render is
    reported while the draft is being written rather than after it is uploaded.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.
        directory: Where the draft is, and so what the images it names are beside.

    Returns:
        One :data:`Finding` per problem, named by the field of the draft it is in
        rather than by the question and part of the export, so that a line of it can be
        acted on with `field replace`. A problem about no one field - the set as a
        whole failing to compile - keeps the validator's own naming of where it is.

    Warns:
        UserWarning: pandoc or xelatex is not installed, so the set was not compiled.
    """
    where = located(draft)
    if not where:
        # A draft with no question in it yet describes an empty set, which has nothing
        # to find and is not worth a xelatex run to find it in.
        return []

    missing = pdf.missing_tools()
    if missing:
        # As `_katex_rejections` does without Node: a check that cannot be run here says
        # what to install and leaves the rest of the report alone.
        warnings.warn(
            "The set the draft describes was not compiled as the PDF generator would: "
            "install " + " and ".join(missing),
            stacklevel=3,
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
            # Whatever the location says past the field: KaTeX names the characters of
            # it that it stopped at, and those are the field's characters here as well.
            rest = problem.location[len(location) :]
            finding = {
                "check": "problem",
                "field": key,
                "ranges": ranges,
                "message": f"{key}{_where(ranges)}{rest}: {problem.message}",
            }
        else:
            finding = {
                "check": "problem",
                "field": "",
                "ranges": [],
                "message": str(problem),
            }
        if finding not in found:
            # A question's solution answers every part of it that has no solution of its
            # own, so one fault in it is found once per part. They are the same field,
            # the same lines and the same wording: a second line of the report saying so
            # is a `field replace` that would be refused for finding nothing to replace.
            found.append(finding)
    return found


def findings(draft: dict[str, Any], directory: str = ".") -> list[Finding]:
    """Everything wrong with a draft: the checks over it and the set it describes.

    This is what a draft's ``report`` is, wherever one is worked out - :func:`validate`
    writing it, or `in2lambda.draft.replay` rebuilding it to compare - so that the two
    cannot arrive at different reports for the same draft.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.
        directory: Where the draft is, and so what the images it names are beside.

    Returns:
        One :data:`Finding` per thing found, in the order :func:`checks` reports in.
    """
    return sorted(checks(draft) + problems(draft, directory), key=_order)


def validate(directory: str = ".") -> list[Finding]:
    """Checks the draft in a directory over and writes the report into it.

    The report replaces whatever one is there, and is dropped again by the next command
    that changes the draft: it describes the draft as it stood, and a report saying
    something else is worse than none at all.

    Args:
        directory: Where the ``draft.json`` to check is.

    Returns:
        What the checks and `in2lambda.validation` found, as it was written into the
        draft.

    Raises:
        DraftMissing: there is no draft in that directory.
        DraftUnreadable: what is there is not a draft anything here wrote.
        SourceUnreadable: the markdown the draft names has moved, or is not text.
        DraftExists: the markdown has changed since the draft was written from it, so
            the lines the report named would not be the lines it was written about.

    Warns:
        UserWarning: a check could not be run here - see :func:`problems`.
    """
    draft, _ = frozen(directory)
    draft["report"] = findings(draft, directory)
    save(Path(directory) / DRAFT, draft)
    return draft["report"]
