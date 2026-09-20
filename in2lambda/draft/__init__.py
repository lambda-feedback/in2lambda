"""Builds up a draft by commands, and rebuilds it from the ones it recorded.

A draft is written by a sequence of commands, some of them chosen by a model. Every
command that changes one is recorded in the draft's ``log`` as it is applied, and every
field a command writes carries where it came from, so that :func:`replay` can build the
same draft again out of the frozen markdown and the log alone, with no model in the loop.
That is what makes a run reproducible, and a saved run a test.

Commands reach a draft only through :func:`apply`, which is what keeps the log complete:
a handler registered with :func:`command` is never called by anything else.
"""

import re
from collections.abc import Callable  # Rather than typing's, which beartype warns on.
from pathlib import Path
from typing import Any

from in2lambda.source import (
    DRAFT,
    SourceError,
    _require_conversion_tools,
    blocks,
    frozen,
    save,
    serialise,
)

Command = dict[str, Any]
"""One entry of the log: ``{"command": name, "args": {...}, "by": who}``."""

Handler = Callable[[dict[str, Any], str, dict[str, Any], str], str]
"""What a command does: `handler(draft, markdown, args, by)`, changing the draft.

The frozen markdown is passed in rather than read, so that a handler quoting the source
by line range quotes the same text on a replay as it did when it first ran. What comes
back is what the command wrote, named - the key of the field, or the block ids a split
made - which is what whoever ran it needs in the command after this one.
"""

_HANDLERS: dict[str, Handler] = {}
"""Every command there is, by the name a log entry names it with."""

_RANGE = re.compile(r"s(\d+)(?::(\d+))?")
"""Lines of the frozen source, as ``s16`` for one of them or ``s10:14`` for several."""


class MalformedCommand(SourceError):
    """A log holds something that is not a command, so nothing can be made of it."""


class UnknownCommand(SourceError):
    """A log names a command that nothing registered, so the draft cannot be rebuilt."""


class NoSuchBlock(SourceError):
    """A command names a block the frozen source has not got."""


class NoSuchLines(SourceError):
    """A command names lines the frozen source has not got, or names them as nothing."""


class NoSuchQuestion(SourceError):
    """A command adds to a question nothing has written yet."""


class AlreadyFilled(SourceError):
    """A command would write a field that is written, or lines another field took."""


class ReplayDiffers(SourceError):
    """Replaying a draft's log does not reproduce the draft."""


def command(name: str) -> Callable[[Handler], Handler]:
    """Registers a handler as the command of that name.

    Args:
        name: What a log entry calls it, as it is typed: ``"mark ignore"``.

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
) -> str:
    """Writes one field of a draft, with where it came from.

    Args:
        draft: The draft to write into.
        key: What the field is called, unique within the draft.
        value: What it is.
        layer: What wrote it: 1 a spec, 2 a predicate, 3 a range taken from the source,
            4 a literal someone typed. A reader deciding whether to trust a field wants
            to know which of those it was.
        ranges: The line ranges of the frozen source the value was copied from, as
            ``[[start, end], ...]``, and empty where it was not copied from any.
        by: Who ran the command, as a name or a model.
        edited: Whether the value is something other than what the source says. A
            literal is the one thing a command writes that arrives edited; otherwise a
            field is edited when something later replaces what a command wrote.

    Returns:
        The key, so that a handler can hand back the field it wrote.

    Raises:
        AlreadyFilled: the field is written already, or the lines it was to be copied
            from are where another field came from. Nothing here changes a field once it
            is written, so either is a mistake, and worth naming both halves of.
    """
    if key in draft["fields"]:
        raise AlreadyFilled(
            f"{key} is already written, and no command here changes a field that is. "
            "Run in2lambda source add --start-over to begin the draft again."
        )
    for filled, field in draft["fields"].items():
        for taken in field["ranges"]:
            if any(taken[0] <= end and start <= taken[1] for start, end in ranges):
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
    }
    return key


def _fault(entry: Any) -> str:
    """What is wrong with the shape of a log entry, or "" if nothing is."""
    if not isinstance(entry, dict):
        return "is not an object"
    if missing := sorted({"command", "args", "by"} - entry.keys()):
        return f"has no {' or '.join(missing)}"
    if not isinstance(entry["command"], str):
        return f"gives {entry['command']!r} as its command, which is not a name"
    if not isinstance(entry["args"], dict):
        return f"gives {entry['args']!r} as its args, which is not an object"
    return ""


def _argument(args: dict[str, Any], name: str, command: str) -> Any:
    """One argument of a command, given that the log entry gave it.

    Handlers take their arguments through this rather than indexing, so that a log
    entry missing one says which one rather than raising a KeyError at whoever ran it.

    Raises:
        MalformedCommand: the entry has no argument of that name.
    """
    if name not in args:
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: it has no "
            f'"{name}" argument.'
        )
    return args[name]


def apply(draft: dict[str, Any], markdown: str, entry: Any) -> str:
    """Runs one command against a draft and records it in the draft's log.

    Args:
        draft: The draft to change, in place.
        markdown: The frozen markdown the draft was written from.
        entry: The command, as it is written in the log. Anything at all, rather than a
            `Command`, because a log is read from a file anyone can edit: what shape it
            has is something to tell the reader about, not something to assume.

    Returns:
        What the command wrote, as the handler names it.

    Raises:
        MalformedCommand: the entry is not a command.
        UnknownCommand: nothing is registered under that name.
    """
    if fault := _fault(entry):
        raise MalformedCommand(
            f"{entry!r} in the log is not a command: it {fault}. A command is an "
            'object with a "command" naming it, its "args", and who it was run "by".'
        )
    if (handler := _HANDLERS.get(entry["command"])) is None:
        raise UnknownCommand(
            f"{entry['command']} is not a command this version of in2lambda has, so "
            "the draft cannot be built from its log. It was written by a newer one."
        )
    written = handler(draft, markdown, entry["args"], entry["by"])
    # After the handler, so a command that was refused is not recorded as having run.
    draft["log"].append(entry)
    return written


def execute(entry: Command, directory: str = ".") -> str:
    """Runs one command against the draft in a directory and writes it back.

    Args:
        entry: The command, as it is written in the log.
        directory: Where the ``draft.json`` to change is.

    Returns:
        What the command wrote, as the handler names it: the key of a field, or the
        block ids a split made.

    Raises:
        SourceError: the draft is missing, is not one of ours, or was written from
            markdown that has changed since; or the command is unknown or refused.
    """
    draft, markdown = frozen(directory)
    written = apply(draft, markdown, entry)
    save(Path(directory) / DRAFT, draft)
    return written


def replay(directory: str = ".") -> None:
    """Rebuilds the draft in a directory from its source and its log, and checks it.

    Nothing is written: the point is to find out whether what is on disk is what its
    commands say it should be, and a replay that wrote the answer could not tell anyone
    it was different.

    Args:
        directory: Where the ``draft.json`` to replay is.

    Raises:
        DraftExists: the markdown has changed since the draft was written from it, so
            the commands would be replayed against lines they were not run against.
        MalformedCommand: the log holds something that is not a command.
        UnknownCommand: the log names a command nothing here registered.
        ReplayDiffers: the rebuilt draft is not the one on disk, byte for byte.
    """
    _require_conversion_tools()
    draft, markdown = frozen(directory)
    # From the markdown rather than from the draft: the blocks are as much a product of
    # the source as the fields are, and copying them across would not check them.
    rebuilt: dict[str, Any] = {
        "source": draft["source"],
        "hash": draft["hash"],
        "blocks": [block.to_dict() for block in blocks(markdown)],
        "log": [],
        "fields": {},
    }
    for entry in draft["log"]:
        apply(rebuilt, markdown, entry)

    path = Path(directory) / DRAFT
    if serialise(rebuilt) != path.read_bytes():
        raise ReplayDiffers(
            f"Replaying the log in {DRAFT} does not reproduce it, so what is in it did "
            "not all come from the commands it records - something has changed it since "
            "they ran. Run in2lambda source add --start-over to begin again."
        )


def _block(draft: dict[str, Any], block: str) -> dict[str, Any]:
    """One block of the frozen source, given the draft has one of that id.

    Raises:
        NoSuchBlock: it has not.
    """
    if (found := next((b for b in draft["blocks"] if b["id"] == block), None)) is None:
        raise NoSuchBlock(
            f"There is no block {block} in {DRAFT}. Run in2lambda source show to see "
            "the ids of the blocks there are."
        )
    return found


def _lines(
    draft: dict[str, Any], markdown: str, where: str, command: str
) -> tuple[int, int]:
    """The first and last line of the source that a ``text`` argument names.

    A block id says the lines are whatever that block spans, which is what an author
    reading `show` has in front of them; a range says them outright, for the part of a
    block that is not worth splitting in two.

    Raises:
        NoSuchBlock: it is neither a range nor a block the frozen source has.
        NoSuchLines: it is a range of lines the source has not got.
    """
    # Block ids are b1, b2, b3a, so anything starting with an s was meant as a range and
    # is answered as one, rather than as a block of that name nobody was looking for.
    if not where.startswith("s"):
        found = _block(draft, where)
        return found["start"], found["end"]
    lines = len(markdown.splitlines())
    if (named := _RANGE.fullmatch(where)) is not None:
        start, end = int(named[1]), int(named[2] or named[1])
        if 1 <= start <= end <= lines:
            return start, end
    raise NoSuchLines(
        f"{command} was given {where}, which is not lines of the frozen source: it has "
        f"{lines} lines, and they are named as s16, or as s10:14 for a range running "
        "from an earlier line to a later. Run in2lambda source show to see them "
        "numbered."
    )


def _fill(
    draft: dict[str, Any],
    markdown: str,
    args: dict[str, Any],
    by: str,
    *,
    command: str,
    key: str,
) -> str:
    """Writes the field a command fills, from its ``text`` or its ``literal``.

    A field is copied out of the frozen source by ``text``, which is what freezing it
    was for, or typed out as a ``literal`` where the source does not say it in a form
    the field can take. A literal is nobody's quotation: it is layer 4, it has no range
    behind it, and it arrives edited, because what it holds is not what the source says.

    Raises:
        MalformedCommand: the command gives both of them, or neither.
        NoSuchBlock, NoSuchLines: its ``text`` is not somewhere in the source.
        AlreadyFilled: the field, or the lines it names, are taken.
    """
    text, literal = args.get("text"), args.get("literal")
    if text is not None and literal is not None:
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: it gives both a "
            '"text" and a "literal", and a field is either copied from the source or '
            "typed out, not both."
        )
    if text is None and literal is None:
        raise MalformedCommand(
            f"{args!r} in the log is not a command {command} can run: it gives neither "
            'a "text" nor a "literal", so there is nothing for it to write.'
        )
    if literal is not None:
        return record(draft, key, literal, layer=4, ranges=[], by=by, edited=True)
    start, end = _lines(draft, markdown, text, command)
    return record(
        draft,
        key,
        "\n".join(markdown.splitlines()[start - 1 : end]),
        layer=3,
        ranges=[[start, end]],
        by=by,
    )


def _next(draft: dict[str, Any], prefix: str) -> str:
    """The first of ``{prefix}1``, ``{prefix}2``... the draft has no text for.

    Ids are worked out rather than given, so that replaying a log numbers the questions
    and their parts exactly as the run that recorded it did.
    """
    number = 1
    while f"{prefix}{number}.text" in draft["fields"]:
        number += 1
    return f"{prefix}{number}"


def _require_question(draft: dict[str, Any], question: str, command: str) -> None:
    """Checks the draft has the question a command adds to.

    Raises:
        NoSuchQuestion: nothing has written that question's text, so there is nothing
            for a part or a solution to belong to.
    """
    if f"{question}.text" not in draft["fields"]:
        raise NoSuchQuestion(
            f"There is no question {question} in {DRAFT}: {command} adds to a question "
            "that in2lambda draft question add has already written."
        )


@command("mark ignore")
def _mark_ignore(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str
) -> str:
    """Marks one block of the frozen source as nothing to take a question from."""
    block = _argument(args, "block", "mark ignore")
    found = _block(draft, block)
    return record(
        draft,
        f"{block}.ignore",
        True,
        layer=3,
        ranges=[[found["start"], found["end"]]],
        by=by,
    )


@command("question add")
def _question_add(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str
) -> str:
    """Adds a question, taking the first number no question has taken."""
    return _fill(
        draft,
        markdown,
        args,
        by,
        command="question add",
        key=f"{_next(draft, 'q')}.text",
    )


@command("part add")
def _part_add(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str
) -> str:
    """Adds a part to a question, taking the first number that question has not."""
    question = _argument(args, "question", "part add")
    _require_question(draft, question, "part add")
    return _fill(
        draft,
        markdown,
        args,
        by,
        command="part add",
        key=f"{_next(draft, f'{question}.p')}.text",
    )


@command("question solution")
def _question_solution(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str
) -> str:
    """Gives a question its worked solution, wherever in the source it is written."""
    question = _argument(args, "question", "question solution")
    _require_question(draft, question, "question solution")
    return _fill(
        draft,
        markdown,
        args,
        by,
        command="question solution",
        key=f"{question}.solution",
    )


@command("split block")
def _split_block(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str
) -> str:
    """Cuts one block of the frozen source in two, so each half can be named.

    A block is whatever the parser made of the source, which is sometimes two things: a
    question and the part under it, written with no blank line between them. The source
    is untouched and the halves are ``b3a`` and ``b3b``, so a replay, which rebuilds the
    blocks from the markdown and then runs the log over them, arrives at the same ids.
    """
    block = _argument(args, "block", "split block")
    at = _argument(args, "at", "split block")
    if not isinstance(at, int):
        raise MalformedCommand(
            f'{args!r} in the log is not a command split block can run: its "at" is '
            f"{at!r} rather than a line number."
        )
    found = _block(draft, block)
    if not found["start"] < at <= found["end"]:
        raise NoSuchLines(
            f"{block} is lines {found['start']}-{found['end']}, so it cannot be split "
            f"at line {at}: the line split at is the first line of the second half, and "
            "each half has to have a line in it."
        )
    index = draft["blocks"].index(found)
    draft["blocks"][index : index + 1] = [
        {**found, "id": f"{block}a", "end": at - 1},
        {**found, "id": f"{block}b", "start": at},
    ]
    return f"{block}a and {block}b"
