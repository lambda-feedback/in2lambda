"""Builds up a draft by commands, and rebuilds it from the ones it recorded.

A draft is written by a sequence of commands, some of them chosen by a model. Every
command that changes one is recorded in the draft's ``log`` as it is applied, and every
field a command writes carries where it came from, so that :func:`replay` can build the
same draft again out of the frozen markdown and the log alone, with no model in the loop.
That is what makes a run reproducible, and a saved run a test.

Commands reach a draft only through :func:`apply`, which is what keeps the log complete:
a handler registered with :func:`command` is never called by anything else.
"""

from collections.abc import Callable  # Rather than typing's, which beartype warns on.
from pathlib import Path
from typing import Any

import in2lambda.spec
from in2lambda.source import (
    DRAFT,
    SourceError,
    _digest,
    _elements,
    _require_conversion_tools,
    blocks,
    frozen,
    save,
    serialise,
)

Command = dict[str, Any]
"""One entry of the log: ``{"command": name, "args": {...}, "by": who}``."""

Handler = Callable[[dict[str, Any], str, dict[str, Any], str, str], None]
"""What a command does: `handler(draft, markdown, args, by, directory)`.

The frozen markdown is passed in rather than read, so that a handler quoting the source
by line range quotes the same text on a replay as it did when it first ran. The
directory is where the draft is, which is what a file named in the log is relative to.
"""

_HANDLERS: dict[str, Handler] = {}
"""Every command there is, by the name a log entry names it with."""


class MalformedCommand(SourceError):
    """A log holds something that is not a command, so nothing can be made of it."""


class UnknownCommand(SourceError):
    """A log names a command that nothing registered, so the draft cannot be rebuilt."""


class NoSuchBlock(SourceError):
    """A command names a block the frozen source has not got."""


class ReplayDiffers(SourceError):
    """Replaying a draft's log does not reproduce the draft."""


class SpecChanged(SourceError):
    """The spec file a log names is not the one that ran: it has changed, or gone."""


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
) -> None:
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
    """
    draft["fields"][key] = {
        "value": value,
        "layer": layer,
        "ranges": ranges,
        # A field is edited when something replaces the value a command wrote, which is
        # not something a command can do to its own field on the way in.
        "edited": False,
        "by": by,
    }


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


def apply(
    draft: dict[str, Any], markdown: str, entry: Any, directory: str = "."
) -> None:
    """Runs one command against a draft and records it in the draft's log.

    Args:
        draft: The draft to change, in place.
        markdown: The frozen markdown the draft was written from.
        entry: The command, as it is written in the log. Anything at all, rather than a
            `Command`, because a log is read from a file anyone can edit: what shape it
            has is something to tell the reader about, not something to assume.
        directory: Where the draft is, and so what a file the command names is beside.

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
    handler(draft, markdown, entry["args"], entry["by"], directory)
    # After the handler, so a command that was refused is not recorded as having run.
    draft["log"].append(entry)


def execute(entry: Command, directory: str = ".") -> dict[str, Any]:
    """Runs one command against the draft in a directory and writes it back.

    Args:
        entry: The command, as it is written in the log.
        directory: Where the ``draft.json`` to change is.

    Returns:
        The draft as the command left it, for whatever wants to report on it.

    Raises:
        SourceError: the draft is missing, is not one of ours, or was written from
            markdown that has changed since; or the command is unknown or refused.
    """
    draft, markdown = frozen(directory)
    apply(draft, markdown, entry, directory)
    save(Path(directory) / DRAFT, draft)
    return draft


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
        SpecChanged: a spec the log was run with has changed or gone since.
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
        apply(rebuilt, markdown, entry, directory)

    path = Path(directory) / DRAFT
    if serialise(rebuilt) != path.read_bytes():
        raise ReplayDiffers(
            f"Replaying the log in {DRAFT} does not reproduce it, so what is in it did "
            "not all come from the commands it records - something has changed it since "
            "they ran. Run in2lambda source add --start-over to begin again."
        )


def coverage(draft: dict[str, Any]) -> list[str]:
    """The blocks of a draft that nothing has made anything of yet.

    Args:
        draft: The draft to look over.

    Returns:
        The ids of the blocks that are in no field and have not been ignored, in
        document order. A spec run prints these: they are what is left to account for,
        and an empty list is the whole document spoken for.
    """
    ranges = [
        line_range
        for field in draft["fields"].values()
        for line_range in field["ranges"]
    ]
    return [
        block["id"]
        for block in draft["blocks"]
        if f"{block['id']}.ignore" not in draft["fields"]
        and not any(
            start <= block["end"] and block["start"] <= end for start, end in ranges
        )
    ]


@command("mark ignore")
def _mark_ignore(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str, directory: str
) -> None:
    """Marks one block of the frozen source as nothing to take a question from."""
    block = _argument(args, "block", "mark ignore")
    if (found := next((b for b in draft["blocks"] if b["id"] == block), None)) is None:
        raise NoSuchBlock(
            f"There is no block {block} in {DRAFT}. Run in2lambda source show to see "
            "the ids of the blocks there are."
        )
    record(
        draft,
        f"{block}.ignore",
        True,
        layer=3,
        ranges=[[found["start"], found["end"]]],
        by=by,
    )


@command("spec run")
def _spec_run(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str, directory: str
) -> None:
    """Fills in a draft's fields from a spec of selectors over the frozen source."""
    _require_conversion_tools()
    name = _argument(args, "spec", "spec run")
    path = Path(directory) / name
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise SpecChanged(
            f"There is no {name} beside {DRAFT}, and the log says the draft was filled "
            "in from one. Put it back, or start the draft again with in2lambda source "
            "add --start-over."
        ) from None
    # As the source is checked: a spec that has been edited since would fill the fields
    # in differently, and a replay is only a check while it runs what was run before.
    if _digest(raw) != _argument(args, "hash", "spec run"):
        raise SpecChanged(
            f"{name} has changed since it was run against {DRAFT}, so replaying the log "
            "would not write the fields that are in the draft. Put it back, or start "
            "the draft again with in2lambda source add --start-over."
        )

    spec = in2lambda.spec.load(raw.decode("utf-8"))
    fields, ignored = in2lambda.spec.fields(spec, _elements(markdown), markdown)
    for found in fields:
        record(draft, found.key, found.value, layer=1, ranges=found.ranges, by=by)
    lines = {block["id"]: [block["start"], block["end"]] for block in draft["blocks"]}
    # The field `mark ignore` writes, so that coverage need not care which said so.
    for block_id in ignored:
        record(
            draft, f"{block_id}.ignore", True, layer=1, ranges=[lines[block_id]], by=by
        )
