"""Builds a draft up by commands, and rebuilds it from the commands it recorded.

A sequence of commands writes a draft, and a model chooses some of them. :func:`apply`
records every command that changes a draft in the draft's ``log``, and every field a
command writes records where its value came from, so that :func:`replay` builds the same
draft again from the frozen markdown and the log alone, with no model involved. A saved
run is therefore a test.

Commands reach a draft only through :func:`apply`, which keeps the log complete: nothing
else calls a handler registered with :func:`command`.
"""

import re
from collections.abc import Callable  # Rather than typing's, which beartype warns on.
from pathlib import Path
from typing import Any

import in2lambda.spec
from in2lambda.draft.report import _order, _where, checks, overlapping, uncovered
from in2lambda.source import (
    SourceError,
    _digest,
    _elements,
    _numbered,
    _require_conversion_tools,
    blocks,
    dedented,
    frozen,
    save,
    serialise,
)

Command = dict[str, Any]
"""One entry of the log: ``{"command": name, "args": {...}, "by": who}``."""

Handler = Callable[[dict[str, Any], list[str], dict[str, Any], str, str], str]
"""What a command does: `handler(draft, sources, args, by, directory)`.

The caller passes the frozen markdown of every source in, in the order the draft froze
them, so that a handler quoting a source by line range quotes the same text on a replay
as it did on the first run. `directory` is the directory the draft is in, which holds any
file the command names. A handler returns the key of the field it wrote, or the block ids
a split made. The caller needs that name for the next command, and a spec run, which
writes a draft's worth of fields, returns the blocks it matched to no field.
"""

_HANDLERS: dict[str, Handler] = {}
"""Every command, by the name a log entry calls it."""

_RANGE = re.compile(r"s(\d+)(?::(\d+))?")
"""Lines of a frozen source, as ``s16`` for one of them or ``s10:14`` for several."""

_QUALIFIED = re.compile(r"(\d+)/([^/]*)")
"""A block id or a line range with its source in front: ``2/b3``, ``2/s10:14``.

One number and one slash: what follows the slash is an id or a range, and never another
source number. So ``1/2/b3`` matches nothing here, and is refused as the address
``1/2/b3`` instead of being read as source 1's ``2/b3``.
"""


class MalformedCommand(SourceError):
    """A log holds an entry that is not a command."""


class UnknownCommand(SourceError):
    """A log names a command this version of in2lambda does not have."""


class NoSuchBlock(SourceError):
    """A command names a block no frozen source holds."""


class NoSuchLines(SourceError):
    """A command names lines no frozen source holds, or writes a range as nothing."""


class NoSuchQuestion(SourceError):
    """A command adds to a question no command has written."""


class AlreadyFilled(SourceError):
    """A command would write a written field, or lines another field was taken from."""


class NoSuchField(SourceError):
    """A command changes the wording of a field the draft does not hold as text."""


class NotOnce(SourceError):
    """The wording a command replaces occurs in the field other than once."""


class ReplayDiffers(SourceError):
    """Replaying a draft's log does not reproduce the draft."""


class SpecChanged(SourceError):
    """A file a log names - a spec, or its predicates - is not the file that ran.

    The file has changed since the run, or it has been deleted.
    """


def command(name: str) -> Callable[[Handler], Handler]:
    """Registers a handler as the command of that name.

    Args:
        name: The name a log entry gives the command, as a reader types it:
            ``"mark ignore"``.

    Returns:
        The decorator, which returns the handler unchanged.
    """

    def register(handler: Handler) -> Handler:
        _HANDLERS[name] = handler
        return handler

    return register


def record(
    draft: dict[str, Any],
    key: str,
    value: Any,
    *,
    layer: int,
    ranges: list[list[int]],
    by: str,
    edited: bool = False,
    source: int = 1,
) -> str:
    """Writes one field of a draft, with where it came from.

    Args:
        draft: The draft to write into.
        key: The name of the field, unique within the draft.
        value: The value to write.
        layer: What wrote the value: 1 a spec, 2 a predicate, 3 a range taken from the
            source, 4 a literal a reader typed. A reader deciding how far to trust a
            field reads the layer.
        ranges: The line ranges of the frozen source the value was copied from, as
            ``[[start, end], ...]``, and empty where the value was copied from none.
        by: Who ran the command, as a person's name or a model.
        edited: Whether the value differs from the source's wording. A literal is the one
            value a command writes that arrives edited; every other field is edited when
            a later command replaces the wording.
        source: Which of the draft's frozen sources the ranges are lines of, numbered
            from 1. The field records the number only where it is not 1, so that a draft
            of one document holds the fields it has always held.

    Returns:
        The key, so that a handler returns the field it wrote.

    Raises:
        AlreadyFilled: the field is written already, or the lines to copy from are the
            lines another field of the same source was copied from. No command fills a
            field twice: `field replace` changes the wording of a written field, and
            `field set` quotes other lines into a written field. The message names the
            field, and for taken lines both fields.
    """
    if key in draft["fields"]:
        raise AlreadyFilled(
            f"{key} is already written, and no command fills a field twice. Run "
            f"in2lambda draft field replace to change the wording {key} holds, "
            f"in2lambda draft field set to quote other lines into {key}, or "
            "in2lambda source add --start-over to begin the draft again."
        )
    for filled, field in draft["fields"].items():
        # Only fields quoted from the same source: line 12 of the solutions document is
        # not line 12 of the sheet, so two fields quoting line 12 quote different text.
        if field.get("source", 1) != source:
            continue
        # Each range on its own, so that the message names the range in the way: a field
        # edited by hand holds several ranges, and the others may be lines this command
        # is free to take.
        for taken in field["ranges"]:
            if overlapping(ranges, [taken]):
                raise AlreadyFilled(
                    f"Lines {taken[0]}-{taken[1]} are where {filled} came from, so "
                    f"they cannot also be {key}. Run in2lambda source show to see "
                    "which lines are still free."
                )
    draft["fields"][key] = {
        "value": value,
        "layer": layer,
        "ranges": ranges,
        "edited": edited,
        "by": by,
        **({"source": source} if source != 1 else {}),
    }
    return key


def _fault(entry: Any) -> str:
    """What is wrong with the shape of a log entry, or "" if nothing is wrong."""
    if not isinstance(entry, dict):
        return "is not an object"
    if missing := sorted({"command", "args", "by"} - entry.keys()):
        return f"has no {' or '.join(missing)}"
    if not isinstance(entry["command"], str):
        return f"gives {entry['command']!r} as its command, which is not a name"
    if not isinstance(entry["args"], dict):
        return f"gives {entry['args']!r} as its args, which is not an object"
    return ""


def _checked(entry: Any) -> Command:
    """One entry of a log, where that entry has the shape of a command.

    Both readers of a log call this - the one applying an entry, and the one reading the
    entries already applied - so that a hand-edited log raises the same message whichever
    reads it first.

    Raises:
        MalformedCommand: the entry is not a command.
    """
    if fault := _fault(entry):
        raise MalformedCommand(
            f"{entry!r} in the log is not a command: it {fault}. A command is an "
            'object with a "command" naming it, its "args", and who it was run "by".'
        )
    return entry


def _argument(args: dict[str, Any], name: str, command: str, kind: type = str) -> Any:
    """One argument of a command, where the log entry gave it as `kind`.

    Handlers read their arguments through this instead of indexing `args`, so that a log
    entry missing an argument, or holding a number where a name belongs, names the
    argument in the message. Every argument is a name except the line a block is split
    at.

    Raises:
        MalformedCommand: the entry has no argument of that name, or has one that is
            not of that kind.
    """
    if name not in args:
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: it has no "
            f'"{name}" argument. Add that argument to the log entry, or start the draft '
            "again with in2lambda source add --start-over."
        )
    if not isinstance(args[name], kind):
        wanted = {int: "a line number", bool: "true or false"}.get(kind, "a name")
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: its "
            f'"{name}" is {args[name]!r} rather than {wanted}. Write {wanted} in the log '
            "entry, or start the draft again with in2lambda source add --start-over."
        )
    return args[name]


def apply(
    draft: dict[str, Any], sources: list[str], entry: Any, directory: str = "."
) -> str:
    """Runs one command against a draft and records it in the draft's log.

    Args:
        draft: The draft to change, in place.
        sources: The frozen markdown of each of the draft's sources, in its order.
        entry: The command, as the log writes it. Typed as Any and not as `Command`,
            because a log is read from a file a reader can edit, so this function
            reports the entry's shape instead of assuming it.
        directory: The directory the draft is in, which holds any file the command names.

    Returns:
        The field key the handler wrote, or the block ids a split made.

    Raises:
        MalformedCommand: the entry is not a command.
        UnknownCommand: nothing is registered under that name.
    """
    entry = _checked(entry)
    if (handler := _HANDLERS.get(entry["command"])) is None:
        raise UnknownCommand(
            f"{entry['command']} is not a command this version of in2lambda has, so "
            "the draft cannot be built from its log. Upgrade in2lambda, or correct the "
            "command name in the log."
        )
    written = handler(draft, sources, entry["args"], entry["by"], directory)
    # After the handler, so a command that was refused is not recorded as having run.
    draft["log"].append(entry)
    # The report describes the draft as it stood, so a command that changes the draft
    # deletes the report.
    draft.pop("report", None)
    return written


def execute(entry: Command, draft: str | Path) -> str:
    """Runs one command against a draft and writes it back.

    Args:
        entry: The command, as it is written in the log.
        draft: The path of the draft to change.

    Returns:
        The field key the handler wrote, the block ids a split made, or the blocks a
        spec run matched to no field.

    Raises:
        SourceError: the draft is missing, is not a draft in2lambda wrote, or was
            written from markdown that has changed since; or the command is unknown or
            refused.
    """
    path = Path(draft)
    found, sources = frozen(path)
    # A handler is given the folder and not the draft, because the files it reads - a
    # spec, a file of predicates - are named from the folder.
    written = apply(found, sources, entry, str(path.parent))
    save(path, found)
    return written


def replay(draft: str | Path) -> None:
    """Rebuilds a draft from its sources and its log, and checks the result matches.

    :func:`replay` writes nothing. :func:`replay` reports whether the draft on disk is the
    draft its commands build, and a replay that wrote its result could report no
    difference.

    Args:
        draft: The path of the draft to replay.

    Raises:
        DraftExists: the markdown has changed since the draft was written from it, so
            the commands would be replayed against lines they were not run against.
        MalformedCommand: the log holds something that is not a command.
        UnknownCommand: the log names a command nothing registered.
        SpecChanged: a spec the log was run with has changed or gone since.
        ReplayDiffers: the rebuilt draft is not the one on disk, byte for byte.
    """
    _require_conversion_tools()
    path = Path(draft)
    found, sources = frozen(path)
    # The blocks are rebuilt from the markdown and not copied from the draft: the blocks
    # come from the sources as the fields do, and copying them would check nothing.
    rebuilt: dict[str, Any] = {
        "sources": [
            {
                "source": source["source"],
                "hash": source["hash"],
                "blocks": [block.to_dict() for block in blocks(markdown, number)],
            }
            for number, (source, markdown) in enumerate(
                zip(found["sources"], sources), start=1
            )
        ],
        "log": [],
        "fields": {},
    }
    for entry in found["log"]:
        apply(rebuilt, sources, entry, str(path.parent))
    # No command writes the report: `in2lambda validate` writes it over the draft the
    # commands left, so a replay runs the checks again. The findings
    # `in2lambda.validation` made over the set are carried across instead, because they
    # depend on whether xelatex and Node.js are installed and the draft does not. Run
    # again on a machine without that toolchain, they would come out shorter, and the
    # replay would report an untouched draft as edited.
    if "report" in found:
        carried = [
            finding for finding in found["report"] if finding["check"] == "problem"
        ]
        rebuilt["report"] = sorted(checks(rebuilt) + carried, key=_order)

    if serialise(rebuilt) != path.read_bytes():
        raise ReplayDiffers(
            f"Replaying the log in {path.name} does not reproduce {path.name}, so some "
            "of its fields did not come from the commands it records: something changed "
            "the draft after those commands ran. Run in2lambda source add --start-over "
            "to begin the draft again."
        )


def _qualified(where: str) -> tuple[int, str]:
    """Which source a block id or a line range belongs to, and the rest of it.

    ``2/b3`` is block b3 of the draft's second source, and ``2/s10:14`` its lines 10 to
    14. An id or range with no number in front belongs to the first source, which is how
    every command written while a draft held one source still reads. ``1/b3`` names the
    block ``b3`` names.

    Anything else is returned as the first source's, under the name it was given, so that
    the caller reports the address a reader typed: ``1/2/b3`` names no block of any
    source and is refused as ``1/2/b3``.
    """
    if (named := _QUALIFIED.fullmatch(where)) is None:
        return 1, where
    return int(named[1]), named[2]


def _block(draft: dict[str, Any], block: str) -> tuple[int, dict[str, Any]]:
    """Which source a block belongs to and the block itself, where a source holds it.

    Raises:
        NoSuchBlock: no source holds that id, either because no block is numbered that
            way or because the draft does not hold the source the id names.
    """
    source, name = _qualified(block)
    wanted = _numbered(source, name)
    found = next(
        (
            held
            for frozen_source in draft["sources"]
            for held in frozen_source["blocks"]
            if held["id"] == wanted
        ),
        None,
    )
    if found is None:
        raise NoSuchBlock(
            f"There is no block {block} in the draft. Run in2lambda source show to see "
            "the ids of the blocks there are."
        )
    return source, found


def _lines(
    draft: dict[str, Any], sources: list[str], where: str, command: str
) -> tuple[int, int, int]:
    """Which source a ``text`` argument names, and its first and last line.

    A block id names the lines that block spans, which `in2lambda source show` prints
    beside it. A range names the lines outright, which quotes part of a block without
    splitting the block. Either names a source after the first by writing that source's
    number in front: ``2/b3``, ``2/s10:14``.

    Raises:
        NoSuchBlock: the argument is neither a range nor a block a frozen source holds.
        NoSuchLines: the argument is a range of lines the source it names does not hold,
            or of a source the draft does not hold.
    """
    source, name = _qualified(where)
    # Block ids are b1, b2, b3a, so a name starting with s is read as a range, and a
    # malformed range is reported as one.
    if not name.startswith("s"):
        in_source, found = _block(draft, where)
        return in_source, found["start"], found["end"]
    if not 1 <= source <= len(sources):
        raise NoSuchLines(
            f"{command} was given {where}, and there is no source {source} in the draft: "
            f"the draft holds {len(sources)}. Run in2lambda source add FILE to freeze "
            "another source beside them."
        )
    lines = len(sources[source - 1].splitlines())
    if (named := _RANGE.fullmatch(name)) is not None:
        start, end = int(named[1]), int(named[2] or named[1])
        if 1 <= start <= end <= lines:
            return source, start, end
    raise NoSuchLines(
        f"{command} was given {where}, which is not lines of source {source}: source "
        f"{source} has {lines} lines. Lines are named s16, or s10:14 for a range running "
        "from an earlier line to a later one, with the source's number in front - "
        "2/s10:14 - for any source after the first. Run in2lambda source show to see the "
        "lines numbered."
    )


def _fill(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    *,
    command: str,
    key: str,
) -> str:
    """Writes the field a command fills, from its ``text`` or its ``literal``.

    ``text`` copies the field out of a frozen source. ``literal`` types the field out
    where no source holds the wording in a form the field takes.
    A literal quotes nothing: it is layer 4, it records no range, and it arrives edited,
    because no source holds its value.

    Raises:
        MalformedCommand: the command gives both arguments, or neither, or gives one of
            them as something other than text.
        NoSuchBlock, NoSuchLines: the command's ``text`` names no lines of a source.
        AlreadyFilled: the field, or the lines it names, are taken.
    """
    text, literal = args.get("text"), args.get("literal")
    if text is not None and literal is not None:
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: it gives both a "
            '"text" and a "literal", and a field is either copied from the source or '
            "typed out, not both. Remove one of the two from the log entry."
        )
    if text is None and literal is None:
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: it gives neither "
            'a "text" nor a "literal", so it names no wording. Add a "text" or a '
            '"literal" to the log entry.'
        )
    # Back through `_argument` now that the choice is settled, so that an argument given
    # as a number is reported by name.
    if literal is not None:
        return record(
            draft,
            key,
            _argument(args, "literal", command),
            layer=4,
            ranges=[],
            by=by,
            edited=True,
        )
    return _quote(
        draft, sources, _argument(args, "text", command), by, command=command, key=key
    )


def _quote(
    draft: dict[str, Any],
    sources: list[str],
    where: str,
    by: str,
    *,
    command: str,
    key: str,
) -> str:
    """Writes a field from the lines of a frozen source that `where` names.

    Raises:
        NoSuchBlock, NoSuchLines: `where` is not somewhere in a source.
        AlreadyFilled: the field, or the lines it names, are taken.
    """
    source, start, end = _lines(draft, sources, where, command)
    return record(
        draft,
        key,
        _quoted(draft, sources[source - 1], source, start, end),
        layer=3,
        ranges=[[start, end]],
        by=by,
        source=source,
    )


def _quoted(
    draft: dict[str, Any], markdown: str, source: int, start: int, end: int
) -> str:
    """Lines of one frozen source as a field holds them.

    Lines quoted out of a list item are dedented by the item's own indentation, which the
    markdown requires and the author did not write. The ranges still name the source
    lines. The block the lines fall in decides whether they are dedented, and the text
    does not, so that a paragraph reading like a list item is quoted as it is written.
    """
    text = "\n".join(markdown.splitlines()[start - 1 : end])
    # Blocks do not overlap, so the block holding the first line is the block the lines
    # belong to. A nested item falls in that block as well, because only a top-level item
    # is a block of its own.
    block = next(
        (
            held
            for held in draft["sources"][source - 1]["blocks"]
            if held["start"] <= start <= held["end"]
        ),
        None,
    )
    return dedented(text) if block and block["type"] == "list item" else text


def _next(draft: dict[str, Any], prefix: str) -> str:
    """The first of ``{prefix}1``, ``{prefix}2``... that the draft holds no text for.

    in2lambda works ids out instead of taking them as arguments, so that replaying a log
    numbers the questions and their parts as the run that recorded it did.
    """
    number = 1
    while f"{prefix}{number}.text" in draft["fields"]:
        number += 1
    return f"{prefix}{number}"


def _require_question(draft: dict[str, Any], question: str, command: str) -> None:
    """Checks that the draft holds the question a command adds to.

    Raises:
        NoSuchQuestion: no command has written that question's text, so a part or a
            solution has no question to belong to.
    """
    if f"{question}.text" not in draft["fields"]:
        raise NoSuchQuestion(
            f"There is no question {question} in the draft: {command} adds to a "
            "question that in2lambda draft question add has already written."
        )


def _text_field(draft: dict[str, Any], key: str, command: str) -> dict[str, Any]:
    """The field of that name, which a command writing into a field reads first.

    Raises:
        NoSuchField: the draft holds no field of that name, or that field holds
            something other than text - `b3.ignore` holds true.
    """
    field = draft["fields"].get(key)
    if field is None or not isinstance(field.get("value"), str):
        raise NoSuchField(
            f"There is no field {key} holding text in the draft. {command} writes into "
            "a field an earlier command wrote."
        )
    return field


@command("mark ignore")
def _mark_ignore(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Marks one block of a frozen source as holding no question, part or solution."""
    source, found = _block(draft, _argument(args, "block", "mark ignore"))
    # The id as the draft holds it, so that a block named 1/b3 writes the b3.ignore that
    # b3 writes, and a block of a later source writes 2/b3.ignore.
    return record(
        draft,
        f"{found['id']}.ignore",
        True,
        layer=3,
        ranges=[[found["start"], found["end"]]],
        by=by,
        source=source,
    )


@command("question add")
def _question_add(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Adds a question, under the first number no question holds."""
    return _fill(
        draft,
        sources,
        args,
        by,
        command="question add",
        key=f"{_next(draft, 'q')}.text",
    )


@command("part add")
def _part_add(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Adds a part to a question, under the first number that question does not hold."""
    question = _argument(args, "question", "part add")
    _require_question(draft, question, "part add")
    return _fill(
        draft,
        sources,
        args,
        by,
        command="part add",
        key=f"{_next(draft, f'{question}.p')}.text",
    )


@command("question solution")
def _question_solution(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Gives a question its worked solution, from wherever the solution is written.

    A solution is often written in a document of its own: ``--text 2/b4`` names the block
    of the solutions frozen beside the sheet.
    """
    question = _argument(args, "question", "question solution")
    _require_question(draft, question, "question solution")
    return _fill(
        draft,
        sources,
        args,
        by,
        command="question solution",
        key=f"{question}.solution",
    )


@command("field replace")
def _field_replace(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Replaces one piece of wording inside a field that is already written.

    An edit is the only fix for some faults: a brace the OCR dropped leaves maths KaTeX
    will not render, and no range of the source holds that maths correctly. The layer
    and the ranges stay as they were, so the change can be shown against the lines the
    field was taken from, and `edited` records that the value differs from those lines.

    Raises:
        MalformedCommand: an argument is missing, or ``regex`` was passed and ``old`` is
            not a regular expression.
        NoSuchField: the draft holds no field of that name holding text.
        NotOnce: ``old`` occurs in the field other than once, so this command cannot
            tell which occurrence was meant.
    """
    key = _argument(args, "field", "field replace")
    old = _argument(args, "old", "field replace")
    new = _argument(args, "new", "field replace")
    # Read only when present, so that a command run without --regex records no argument
    # for it, as every other option does.
    regex = "regex" in args and _argument(args, "regex", "field replace", bool)

    field = _text_field(draft, key, "field replace")
    value = field["value"]
    try:
        found = len(re.findall(old, value)) if regex else value.count(old)
        # A function, not `new` itself, because re.sub reads a string as a template, in
        # which \t is a tab and \frac is an error. This command repairs LaTeX, so NEW is
        # written as it was typed, backslashes and all.
        replaced = (
            re.sub(old, lambda _: new, value, count=1)
            if regex
            else value.replace(old, new, 1)
        )
    except re.error as error:
        raise MalformedCommand(
            f"{args!r} in the log is not a command field replace can run: its OLD is "
            f"not a regular expression - {error}. Correct the pattern in the log entry, "
            "or drop --regex to replace OLD as it is written."
        ) from None
    if found != 1:
        raise NotOnce(
            f"{old!r} occurs {found} times in {key} rather than once, so field replace "
            "cannot tell which occurrence to replace. Give more of the wording around "
            "it, or pass --regex and a pattern that matches one occurrence."
        )

    field["value"] = replaced
    field["edited"] = True
    field["by"] = by
    return key


@command("field set")
def _field_set(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Quotes lines of a frozen source into a field that is already written.

    A spec matching the label line `Q4` alone writes an empty `q4.text`, which
    `in2lambda validate` reports, and another part of the source holds the wording the
    field should hold. `field set` writes the field again from the lines holding that
    wording, at layer 3 with their ranges and `edited` false, as `question add --text`
    writes a field. `field replace` writes text that no line of the source holds.

    `field set` drops the ranges the field named before, because the field's value is no
    longer copied from those lines. `in2lambda validate` then reports those lines as in
    no field, and `in2lambda draft mark ignore` marks a block that holds no question.

    Raises:
        MalformedCommand: the command has no ``field`` or no ``text``.
        NoSuchField: the draft holds no field of that name holding text.
        NoSuchBlock, NoSuchLines: the command's ``text`` is in no source.
        AlreadyFilled: the lines the command names are the lines another field of the
            same source was copied from.
    """
    key = _argument(args, "field", "field set")
    where = _argument(args, "text", "field set")
    _text_field(draft, key, "field set")
    # Deleted before the field is written again, so that `record` checks the lines
    # against the other fields of the source and does not refuse the key it is about to
    # write. The file is unchanged until the command has run, because `execute` saves
    # the draft once `apply` has returned.
    del draft["fields"][key]
    return _quote(draft, sources, where, by, command="field set", key=key)


@command("split block")
def _split_block(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Cuts one block of a frozen source in two, so that each half has an id.

    A block is whatever the parser made of the source, which is sometimes two things: a
    question and the part under it, written with no blank line between them. The source
    is unchanged and the halves are ``b3a`` and ``b3b``, so that a replay, which rebuilds
    the blocks from the markdown and then runs the log over them, arrives at the same
    ids.
    """
    block = _argument(args, "block", "split block")
    at = _argument(args, "at", "split block", int)
    source, found = _block(draft, block)
    if not found["start"] < at <= found["end"]:
        raise NoSuchLines(
            f"{block} is lines {found['start']}-{found['end']}, so it cannot be split "
            f"at line {at}: the line split at is the first line of the second half, and "
            "each half must hold a line."
        )
    held = draft["sources"][source - 1]["blocks"]
    index = held.index(found)
    held[index : index + 1] = [
        {**found, "id": f"{found['id']}a", "end": at - 1},
        {**found, "id": f"{found['id']}b", "start": at},
    ]
    return f"{found['id']}a and {found['id']}b"


def _file_as_run(directory: str, name: str, digest: str) -> bytes:
    """A file the log says a spec run used, where that file still holds what it held.

    Args:
        directory: The directory the draft is in, which holds the file.
        name: The name the log gives the file: the spec, or the predicates it names.
        digest: The hash the log records for the file at the time it ran.

    Returns:
        The contents of the file, for the caller about to run it.

    Raises:
        SpecChanged: no file of that name is beside the draft, or the file is not the one
            the log records running. The fields the spec wrote are then fields no file on
            disk would write again, so neither a replay nor another run can check them.
    """
    try:
        raw = (Path(directory) / name).read_bytes()
    except FileNotFoundError:
        raise SpecChanged(
            f"There is no {name} beside the draft, and the log says the draft was "
            "filled in with it. Put it back, or start the draft again with in2lambda "
            "source add --start-over."
        ) from None
    if _digest(raw) != digest:
        raise SpecChanged(
            f"{name} has changed since it was run against the draft, so the fields the "
            "spec wrote are not the ones it would write now. Put it back, or start the "
            "draft again with in2lambda source add --start-over."
        )
    return raw


def _files(args: dict[str, Any]) -> list[tuple[str, str]]:
    """The files a `spec run` entry says it ran, as ``(name, hash)`` for each file.

    The spec, and then the Python file of predicates the spec named, where it named one.

    Raises:
        MalformedCommand: the entry names a file without its hash, or a hash without its
            file.
    """
    files = [
        (
            _argument(args, "spec", "spec run"),
            _argument(args, "hash", "spec run"),
        )
    ]
    if "predicates" in args or "predicates_hash" in args:
        files.append(
            (
                _argument(args, "predicates", "spec run"),
                _argument(args, "predicates_hash", "spec run"),
            )
        )
    return files


def spec_command(name: str, by: str, draft: str | Path) -> Command:
    """The `spec run` entry for a spec, with the hash of every file it depends on.

    The log records each hash beside the name of its file, so that a replay can check
    that it is running the files that wrote the fields it is checking.

    Args:
        name: The spec to run, as the log is to name it: beside the draft.
        by: Who runs it, as a person's name or a model.
        draft: The path of the draft the spec fills in. The spec is beside that draft.

    Returns:
        The command, for :func:`execute` to run.

    Raises:
        SourceError: pandoc, panflute or pyyaml is missing; the spec cannot be read; or
            it names a file of predicates that is not beside it.
    """
    _require_conversion_tools()
    directory = Path(draft).parent
    try:
        raw = (directory / name).read_bytes()
    except OSError:
        raise in2lambda.spec.BadSpec(
            f"There is no {name} to read a spec from. A spec is the file of selectors "
            "the draft's fields are filled in from."
        ) from None
    args: dict[str, Any] = {"spec": name, "hash": _digest(raw)}
    spec = in2lambda.spec.load(raw)
    if spec.predicates is not None:
        # The predicates file is beside the spec, which is the only place `load`
        # accepts, and the log names it from the draft's directory.
        beside = (Path(name).parent / spec.predicates).as_posix()
        try:
            code = (directory / beside).read_bytes()
        except OSError:
            raise in2lambda.spec.BadSpec(
                f"There is no {beside} to read the spec's predicates from. The "
                "functions a spec calls are in a Python file beside it."
            ) from None
        args |= {"predicates": beside, "predicates_hash": _digest(code)}
    return {"command": "spec run", "args": args, "by": by}


@command("spec run")
def _spec_run(
    draft: dict[str, Any],
    sources: list[str],
    args: dict[str, Any],
    by: str,
    directory: str,
) -> str:
    """Fills a draft's fields in from a spec of selectors over its frozen sources."""
    _require_conversion_tools()
    # Every file every spec run in the log used, and not only the files this entry
    # names: a spec edited since leaves fields the log can no longer reproduce, whatever
    # name that file has now. On a replay this re-reads files that their own entries
    # checked, at one file read each.
    for entry in map(_checked, draft["log"]):
        if entry["command"] == "spec run":
            for file, digest in _files(entry["args"]):
                _file_as_run(directory, file, digest)
    raw = [_file_as_run(directory, file, digest) for file, digest in _files(args)]

    spec = in2lambda.spec.load(raw[0])
    functions = None
    if spec.predicates is not None:
        # The entry names the file, and the spec does not, so that the file run is the
        # file the hash beside it in the log was checked against.
        functions = in2lambda.spec.predicates(
            spec, raw[-1], _argument(args, "predicates", "spec run")
        )
    # The selectors run over the blocks the parser makes of the sources, and a `split
    # block` run since leaves the draft holding halves the parser never made. So an
    # ignored block takes its id and its range from here and not from the draft: the
    # field then spans the whole ignored block, and `uncovered`, which reads the lines a
    # field was taken from, counts each half of a split block as covered.
    documents = [
        (_elements(markdown, number), markdown)
        for number, markdown in enumerate(sources, start=1)
    ]
    fields, ignored, doubled = in2lambda.spec.fields(spec, documents, functions)
    for found in fields:
        record(
            draft,
            found.key,
            found.value,
            layer=1,
            ranges=found.ranges,
            by=by,
            source=found.source,
        )
    lines = {
        block.id: (number, [block.start, block.end])
        for number, (elements, _) in enumerate(documents, start=1)
        for block, _ in elements
    }
    # The field `mark ignore` writes, so that `uncovered` reads one field whichever
    # command wrote it.
    for block_id in ignored:
        source, span = lines[block_id]
        record(
            draft,
            f"{block_id}.ignore",
            True,
            layer=1,
            ranges=[span],
            by=by,
            source=source,
        )
    # A spec writes a draft's worth of fields, so it returns the blocks it matched to no
    # field, for the reader to account for. The wording is `in2lambda validate`'s, because
    # the check is the same.
    reported = [finding["message"] for finding in uncovered(draft)]
    # A doubled block is in no field as well. The message below names the field the block
    # would have been written to and the block already written there, which the coverage
    # report does not name.
    reported += [
        f"{block}{_where(ranges)} would be {key}, which {by_block}"
        f"{_where(by_ranges)} already holds."
        for block, ranges, key, by_block, by_ranges in doubled
    ]
    if reported:
        return "\n".join(reported)
    return "Every block is in a field or ignored."
