"""Freezes a source document, so that its text can be quoted by line range.

Anything that writes questions from a document - the in2lambda agent, say - needs to
take the wording out of the source rather than retype it, and a line range is only an
address if the text it points into cannot move underneath it. So the document is frozen
once: converted to markdown, hashed, and written down beside a ``draft.json`` listing
every top-level block with the lines it spans.

Everything here needs pandoc, and the parsing needs panflute, which only the ``convert``
extra installs; :func:`add` says so rather than failing on the import.
"""

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DRAFT = "draft.json"
"""What a frozen source is written to, beside the source itself."""

_FIELDS = ("source", "hash", "blocks", "log", "fields")
"""What a draft has in it, and so what one has to have for anything here to read it.

A draft written before ``log`` and ``fields`` existed has neither, and is refused as one
nothing here wrote: there is no command log to replay it from, and inventing an empty one
would claim the fields in it came from nowhere. Freezing the source again is the way
through, which is what the refusal says.
"""

_MARKDOWN = "commonmark_x"
"""The dialect the frozen markdown is written in, and read back as.

Writer and reader have to agree: pandoc's ``markdown`` writer emits fenced divs and
bracketed spans that a commonmark reader would take as ordinary text. ``commonmark_x``
also covers the ``$...$`` maths and the ``{width=...}`` attributes a converted document
carries.
"""

_POSITION = re.compile(r"(?:[^@;]*@)?(\d+):\d+-(\d+):(\d+)")
"""One ``line:column-line:column`` of a ``data-pos``, which may name a file and repeat."""


class SourceError(RuntimeError):
    """Freezing or printing a source could not be done, for a reason worth printing.

    The command line turns any of these into a message and a non-zero exit, so
    anything a reader could do something about - a draft from somewhere else, a file
    that has moved - is raised as one of these rather than left as whatever the
    standard library raised on the way past.
    """


class ConversionToolsMissing(SourceError):
    """Document conversion was asked for without pandoc or panflute installed."""


class DraftExists(SourceError):
    """A draft is already there and was not made from this version of the source."""


class DraftMissing(SourceError):
    """There is no draft to show in the directory asked about."""


class DraftUnreadable(SourceError):
    """There is a file where the draft goes, but it is not a draft."""


class SourceUnreadable(SourceError):
    """The markdown to read has moved, or is not text."""


def _require_conversion_tools() -> None:
    missing = []
    if shutil.which("pandoc") is None:
        missing.append("pandoc (see https://pandoc.org/installing.html)")
    if importlib.util.find_spec("panflute") is None:
        missing.append("panflute (pip install 'in2lambda[convert]')")
    if missing:
        raise ConversionToolsMissing(
            f"Converting documents needs {' and '.join(missing)}."
        )


def file_type(file: str) -> str:
    """Determines which pandoc file format to use for a given file.

    See https://github.com/jgm/pandoc/blob/bad922a69236e22b20d51c4ec0b90c5a6c038433/src/Text/Pandoc/Format.hs#L171
    (or any newer commit) for pandoc's supported file extensions.

    Args:
        file: A file path with the file extension included.

    Returns:
        An option in `pandoc --list-input-formats` that matches the given file type

    Examples:
        >>> from in2lambda.source import file_type
        >>> file_type("example.tex")
        'latex'
        >>> file_type("/some/random/path/demo.md")
        'markdown'
        >>> file_type("no_extension")
        Traceback (most recent call last):
        RuntimeError: Unsupported file extension: .no_extension
        >>> file_type("demo.unknown_extension")
        Traceback (most recent call last):
        RuntimeError: Unsupported file extension: .unknown_extension
    """
    match (extension := file.split(".")[-1].lower()):
        case "tex" | "latex" | "ltx":
            return "latex"
        case (
            "md"
            | "rmd"
            | "markdown"
            | "mdown"
            | "mdwn"
            | "mkd"
            | "mkdn"
            | "text"
            | "txt"
        ):
            return "markdown"
        case "docx":
            return "docx"  # Pandoc doesn't seem to support .doc, and panflute doesn't like .docx.
    raise RuntimeError(f"Unsupported file extension: .{extension}")


def _pandoc(file: str, to: str) -> bytes:
    """The given file, as pandoc writes it in the `to` format.

    Undecoded, because what is written to disk and what is hashed have to be the same
    bytes; whoever wants the text of it decodes it themselves.
    """
    return subprocess.check_output(["pandoc", file, "-f", file_type(file), "-t", to])


def _digest(data: bytes) -> str:
    """How a frozen markdown is named in its draft, so that a change to it shows up.

    The bytes of the file, not the text they decode to: the draft is checked by whoever
    is quoting the markdown, who has nothing but the file, and `sha256sum` on it has to
    give the same answer whatever the line endings in it are.
    """
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _source(path: Path) -> tuple[bytes, str]:
    """A markdown file as bytes and as text, given it is still there and still text.

    Both freezing and showing read one, and someone who has moved the file or saved it
    in some other encoding wants telling which it was, not a traceback. The bytes are
    what gets hashed, and `bytes.decode` rewrites no line endings, so the text still
    has whatever the file has.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise SourceUnreadable(
            f"There is no {path}. Put it back, or freeze the document it came from "
            "again with in2lambda source add --start-over."
        ) from None
    try:
        return raw, raw.decode("utf-8")
    except UnicodeDecodeError:
        raise SourceUnreadable(
            f"{path} is not UTF-8 text, so it cannot be read as markdown. Save it as "
            "UTF-8 and try again."
        ) from None


def _draft(path: Path) -> dict[str, Any]:
    """The draft at the given path, given that something here wrote it.

    Raises:
        DraftMissing: nothing is there at all.
        DraftUnreadable: something is, but it is not JSON or it is not a draft. Either
            way it is not this package's to read from or write over.
    """
    if not path.is_file():
        raise DraftMissing(
            f"There is no {DRAFT} in {path.parent.resolve()}. "
            "Run in2lambda source add FILE first."
        )
    advice = (
        "Move it aside and run in2lambda source add FILE, or pass --start-over to "
        "write over it."
    )
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
        fields = draft.keys()
    except (ValueError, AttributeError) as error:
        # AttributeError: valid JSON, but a list or a number rather than an object.
        raise DraftUnreadable(
            f"{path} cannot be read as a draft: {error}. {advice}"
        ) from None
    if missing := [field for field in _FIELDS if field not in fields]:
        raise DraftUnreadable(
            f"{path} is not a draft anything here wrote: it has no "
            f"{' or '.join(missing)} in it. {advice}"
        )
    return draft


def serialise(draft: dict[str, Any]) -> bytes:
    """The bytes a draft is written as, which is the only form it is ever written in.

    Sorted, and bytes rather than text, so that the same draft is the same file:
    replaying a command log has to reproduce ``draft.json`` exactly, which it cannot do
    if the key order depends on what order something happened to write the keys in, or
    if the newlines depend on which machine wrote them.
    """
    return (json.dumps(draft, indent=2, sort_keys=True) + "\n").encode("utf-8")


def save(path: Path, draft: dict[str, Any]) -> None:
    """Writes a draft to the given path."""
    path.write_bytes(serialise(draft))


def frozen(directory: str = ".") -> tuple[dict[str, Any], str]:
    """The draft in a directory and the markdown it was written from, still unmoved.

    Args:
        directory: Where the ``draft.json`` is.

    Returns:
        The draft, and the text of the markdown it names.

    Raises:
        DraftMissing: there is no draft in that directory.
        DraftUnreadable: what is there is not a draft anything here wrote.
        SourceUnreadable: the markdown the draft names has moved, or is not text.
        DraftExists: the markdown has changed since the draft was written from it, so
            the line ranges in the draft no longer name the lines they were taken from.
    """
    path = Path(directory) / DRAFT
    draft = _draft(path)
    raw, markdown = _source(path.parent / draft["source"])
    if _digest(raw) != draft["hash"]:
        raise DraftExists(
            f"{draft['source']} has changed since {DRAFT} was written from it, so its "
            "block ids no longer name the lines they were written against. Run "
            "in2lambda source add --start-over to freeze the file as it now is."
        )
    return draft, markdown


@dataclass
class Block:
    """One top-level block of a frozen source, and the lines it spans.

    Lines are 1-based and inclusive, so `start` and `end` are the numbers
    :func:`show` prints beside that block's first and last line.
    """

    id: str
    type: str
    start: int
    end: int

    def to_dict(self) -> dict[str, str | int]:
        """The block as it is written into ``draft.json``."""
        return {"id": self.id, "type": self.type, "start": self.start, "end": self.end}


def blocks(markdown: str) -> list[Block]:
    r"""Every top-level block of some markdown, in the order it is written.

    Args:
        markdown: A document in the dialect :func:`add` freezes to.

    Returns:
        One :class:`Block` per block, numbered ``b1`` onwards. The blocks do not
        overlap and every line of the document falls in at most one: a block that is
        none of the types the agent quotes is still listed, as ``other``, rather than
        leaving its lines unaddressable.

    Examples:
        >>> from in2lambda.source import blocks
        >>> blocks("# Title\n\nSome words.\n")
        [Block(id='b1', type='heading', start=1, end=1), Block(id='b2', type='paragraph', start=3, end=3)]
    """
    import panflute as pf

    document = pf.convert_text(
        markdown, input_format=f"{_MARKDOWN}+sourcepos", standalone=True
    )
    found = [span for element in document.content for span in _spans(element, pf)]
    # Where no blank line separates one block from the next - a list straight after a
    # paragraph, a definition list - pandoc reports the first as running on into the
    # second's first line, so no block is allowed to reach where the next one starts,
    # nor past the end of the document.
    limits = [start - 1 for _, start, _ in found[1:]] + [len(markdown.splitlines())]
    return [
        Block(f"b{number}", kind, start, min(end, limit))
        for number, ((kind, start, end), limit) in enumerate(zip(found, limits), 1)
    ]


def _spans(element, pf):  # type: ignore[no-untyped-def]
    """The ``(type, start, end)`` triples one top-level element accounts for.

    A list is several: the ticket asks for a list item, not a list, and an item spans
    everything nested under it.
    """
    inner = _unwrapped(element, pf)
    if isinstance(inner, (pf.BulletList, pf.OrderedList)):
        # An item with nothing in it - a lone bullet, which a .docx often has - holds
        # no element to take a position from, so there is no range to give it and it
        # is left out rather than guessed at.
        return [
            ("list item", _range(item.content[0])[0], _range(item.content[-1])[1])
            for item in inner.content
            if len(item.content)
        ]
    return [(_kind(inner, pf), *_range(element))]


def _unwrapped(element, pf):  # type: ignore[no-untyped-def]
    """What an element is, past the Div that `sourcepos` wraps it in.

    Only elements that take attributes of their own (a heading, a table) carry
    ``data-pos`` directly; pandoc wraps the rest in a Div to hang it on.
    """
    if isinstance(element, pf.Div) and element.attributes.get("wrapper"):
        return element.content[0]
    return element


def _kind(inner, pf) -> str:  # type: ignore[no-untyped-def]
    """Which of the ticket's block types an unwrapped element is."""
    if isinstance(inner, pf.Header):
        return "heading"
    if isinstance(inner, (pf.Para, pf.Plain)):
        # A paragraph holding nothing but one image, or one $$...$$, is that thing.
        contents = [
            item
            for element in inner.content
            for item in (element.content if isinstance(element, pf.Span) else [element])
            if not isinstance(item, (pf.Space, pf.SoftBreak))
        ]
        if len(contents) == 1:
            if isinstance(contents[0], pf.Math) and contents[0].format == "DisplayMath":
                return "display maths"
            if isinstance(contents[0], pf.Image):
                return "image"
        return "paragraph"
    return "other"


def _range(element) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    """The first and last line an element covers, from its ``data-pos``.

    An element may carry more than one position, in which case they are parts of it and
    the whole of it is wanted. An end at column 1 means the block stopped before that
    line, which is how pandoc reports every block that ends in a newline.
    """
    positions = _POSITION.findall(element.attributes["data-pos"])
    return (
        min(int(start) for start, _, _ in positions),
        max(
            int(end) - 1 if column == "1" else int(end) for _, end, column in positions
        ),
    )


def add(file: str, start_over: bool = False) -> Path:
    """Freezes a document and writes the draft of it beside the file.

    A .docx or .tex file is converted to markdown next to it; a markdown file is taken
    as it is and nothing is copied. Either way the markdown is hashed and its blocks
    written to ``draft.json``, so that whatever quotes the source by line range can tell
    that the lines it was given still say what they said.

    Args:
        file: The document to freeze, as .docx, .tex or markdown.
        start_over: Freeze the file again, discarding whatever is already there.

    Returns:
        The path of the ``draft.json`` that was written.

    Raises:
        ConversionToolsMissing: pandoc or panflute is not installed.
        SourceUnreadable: the file is markdown, but not UTF-8 text.
        DraftUnreadable: there is a draft.json beside the file that nothing here wrote,
            so it is not ours to read a hash out of or to write over.
        DraftExists: the source has changed since it was frozen, or the markdown would
            overwrite a file that no draft claims. Neither happens with `start_over`.
    """
    _require_conversion_tools()
    source = Path(file)
    if file_type(file) == "markdown":
        raw, markdown = _source(source)
        frozen_path = source
    else:
        raw = _pandoc(file, _MARKDOWN)
        markdown = raw.decode("utf-8")
        frozen_path = source.with_suffix(".md")
    draft = source.parent / DRAFT
    digest = _digest(raw)

    if not start_over:
        if draft.is_file():
            if _draft(draft)["hash"] != digest:
                raise DraftExists(
                    f"{source.name} has changed since {DRAFT} was written from it. "
                    "Run in2lambda source add --start-over to freeze it again, which "
                    "invalidates every line range taken from the old draft."
                )
        elif frozen_path != source and frozen_path.exists():
            raise DraftExists(
                f"{frozen_path.name} is already there and no {DRAFT} claims it, so it "
                "is not ours to overwrite. Move it aside, or run in2lambda source add "
                "--start-over."
            )

    # Before either file is written: a parse that fails half way through would
    # otherwise leave the markdown there with no draft claiming it, and the next run
    # would refuse to touch a file this one wrote.
    found = [block.to_dict() for block in blocks(markdown)]

    if frozen_path != source:
        # The bytes pandoc wrote, so that the file on disk is what `digest` is of;
        # writing text would rewrite the line endings on Windows and it would not be.
        frozen_path.write_bytes(raw)
    # Freezing is where a draft starts, not something it records: a replay is the log
    # applied to this, so `add` is the only thing that writes a draft with nothing in it.
    save(
        draft,
        {
            "source": frozen_path.name,
            "hash": digest,
            "blocks": found,
            "log": [],
            "fields": {},
        },
    )
    return draft


def show(directory: str = ".") -> str:
    """The frozen markdown of a draft, numbered, with block ids in the margin.

    Args:
        directory: Where the ``draft.json`` to print is.

    Returns:
        One line per line of the frozen markdown: the id of the block starting there,
        where one does, then the line number and the line itself.

    Raises:
        DraftMissing: there is no draft in that directory.
        DraftUnreadable: what is there is not a draft anything here wrote.
        SourceUnreadable: the markdown the draft names has moved, or is not text.
        DraftExists: the markdown has changed since the draft was written from it, so
            the ids would be printed against lines they are not the ids of.
    """
    # A line range is only an address while the lines have not moved: printing ids
    # against markdown the draft was not written from would be worse than printing
    # nothing, because it would look right.
    draft, markdown = frozen(directory)

    ids = {block["start"]: block["id"] for block in draft["blocks"]}
    lines = markdown.splitlines()
    margin = max((len(block_id) for block_id in ids.values()), default=0)
    numbers = len(str(len(lines)))
    return "\n".join(
        f"{ids.get(number, ''):>{margin}}  {number:>{numbers}}  {line}".rstrip()
        for number, line in enumerate(lines, start=1)
    )
