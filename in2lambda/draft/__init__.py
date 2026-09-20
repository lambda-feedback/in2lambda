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

Handler = Callable[[dict[str, Any], str, dict[str, Any], str], None]
"""What a command does: `handler(draft, markdown, args, by)`, changing the draft.

The frozen markdown is passed in rather than read, so that a handler quoting the source
by line range quotes the same text on a replay as it did when it first ran.
"""

_HANDLERS: dict[str, Handler] = {}
"""Every command there is, by the name a log entry names it with."""


class UnknownCommand(SourceError):
    """A log names a command that nothing registered, so the draft cannot be rebuilt."""


class NoSuchBlock(SourceError):
    """A command names a block the frozen source has not got."""


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


def apply(draft: dict[str, Any], markdown: str, entry: Command) -> None:
    """Runs one command against a draft and records it in the draft's log.

    Args:
        draft: The draft to change, in place.
        markdown: The frozen markdown the draft was written from.
        entry: The command, as it is written in the log.

    Raises:
        UnknownCommand: nothing is registered under that name.
    """
    if (handler := _HANDLERS.get(entry["command"])) is None:
        raise UnknownCommand(
            f"{entry['command']} is not a command this version of in2lambda has, so "
            "the draft cannot be built from its log. It was written by a newer one."
        )
    handler(draft, markdown, entry["args"], entry["by"])
    # After the handler, so a command that was refused is not recorded as having run.
    draft["log"].append(entry)


def execute(entry: Command, directory: str = ".") -> None:
    """Runs one command against the draft in a directory and writes it back.

    Args:
        entry: The command, as it is written in the log.
        directory: Where the ``draft.json`` to change is.

    Raises:
        SourceError: the draft is missing, is not one of ours, or was written from
            markdown that has changed since; or the command is unknown or refused.
    """
    draft, markdown = frozen(directory)
    apply(draft, markdown, entry)
    save(Path(directory) / DRAFT, draft)


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


@command("mark ignore")
def _mark_ignore(
    draft: dict[str, Any], markdown: str, args: dict[str, Any], by: str
) -> None:
    """Marks one block of the frozen source as nothing to take a question from."""
    block = args["block"]
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
