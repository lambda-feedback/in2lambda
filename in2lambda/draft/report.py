"""Checks a draft over as a whole, and writes what it finds into it.

A draft is written one command at a time, and what a run of them left out is not
something any one command can see: a block nobody quoted, two fields taken from the same
lines, a question numbered 3 where there is no 2, a part with nothing answering it. So
the finished draft is looked over at once, and what the checks find is written into it as
its ``report``, which is what whoever is writing the draft - an agent or a person - reads
to find out what is left to do, without reading the draft itself.

Everything here reports, never refuses: what the checks found may well be deliberate, and
deciding that is whoever is writing the draft's to do. Only what is in the draft is
looked at - its blocks, its field keys, their ranges and their values - because what the
text of a question says is `in2lambda.validation`'s, at export.
"""

import re
from pathlib import Path
from typing import Any

from in2lambda.source import DRAFT, frozen, save

Finding = dict[str, Any]
"""One thing a check found: ``{"check", "field", "ranges", "message"}``.

``check`` is which check found it, ``field`` the block id or field key it is about,
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
    """Blocks of the sources that no field, and no `mark ignore`, accounts for.

    A block partly quoted is reported for the rest of it: a question taken from the first
    line of a block leaves the other lines as much unaccounted for as a whole block would.
    Blocks are accounted for by the lines the fields were taken from rather than by name,
    so that a block `split block` has cut in two is covered by an ignore of the whole.

    Args:
        draft: A draft, as `in2lambda.source.frozen` reads one.

    Returns:
        One :data:`Finding` per block with lines nothing has made anything of, in
        document order and source by source. `in2lambda.spec` reports through this as
        well as the checks do: what a spec run left out is the same question asked the
        moment it finishes.
    """
    # By source as well as by line: line 12 of the solutions document is not line 12 of
    # the sheet, and a field quoting the one accounts for nothing in the other.
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
        # Of the same source, since the same lines of two documents are not the same
        # lines, as `in2lambda.draft.record` compares them.
        if fields[key].get("source", 1) == fields[other].get("source", 1)
        and overlapping(fields[key]["ranges"], fields[other]["ranges"])
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
    return sorted(
        found,
        key=lambda finding: (
            finding["ranges"][0][0] if finding["ranges"] else _UNPLACED,
            finding["field"],
        ),
    )


def validate(directory: str = ".") -> list[Finding]:
    """Checks the draft in a directory over and writes the report into it.

    The report replaces whatever one is there, and is dropped again by the next command
    that changes the draft: it describes the draft as it stood, and a report saying
    something else is worse than none at all.

    Args:
        directory: Where the ``draft.json`` to check is.

    Returns:
        What the checks found, as it was written into the draft.

    Raises:
        DraftMissing: there is no draft in that directory.
        DraftUnreadable: what is there is not a draft anything here wrote.
        SourceUnreadable: a markdown the draft names has moved, or is not text.
        DraftExists: a markdown has changed since the draft was written from it, so
            the lines the report named would not be the lines it was written about.
    """
    draft, _ = frozen(directory)
    draft["report"] = checks(draft)
    save(Path(directory) / DRAFT, draft)
    return draft["report"]
