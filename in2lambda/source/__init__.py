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

DRAFT = "draft.json"
"""What a frozen source is written to, beside the source itself."""

_MARKDOWN = "commonmark_x"
"""The dialect the frozen markdown is written in, and read back as.

Writer and reader have to agree: pandoc's ``markdown`` writer emits fenced divs and
bracketed spans that a commonmark reader would take as ordinary text. ``commonmark_x``
also covers the ``$...$`` maths and the ``{width=...}`` attributes a converted document
carries.
"""

_POSITION = re.compile(r"(?:[^@;]*@)?(\d+):\d+-(\d+):(\d+)")
"""One ``line:column-line:column`` of a ``data-pos``, which may name a file and repeat."""


class ConversionToolsMissing(RuntimeError):
    """Document conversion was asked for without pandoc or panflute installed."""


class DraftExists(RuntimeError):
    """A draft is already there and was not made from this version of the source."""


class DraftMissing(RuntimeError):
    """There is no draft to show in the directory asked about."""


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


def _pandoc(file: str, to: str) -> str:
    """The given file, as pandoc writes it in the `to` format."""
    output = subprocess.check_output(["pandoc", file, "-f", file_type(file), "-t", to])
    return output.decode("utf-8")


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
    return [
        Block(f"b{number}", kind, start, end)
        for number, (kind, start, end) in enumerate(found, start=1)
    ]


def _spans(element, pf):  # type: ignore[no-untyped-def]
    """The ``(type, start, end)`` triples one top-level element accounts for.

    A list is several: the ticket asks for a list item, not a list, and an item spans
    everything nested under it.
    """
    inner = _unwrapped(element, pf)
    if isinstance(inner, (pf.BulletList, pf.OrderedList)):
        return [
            ("list item", _range(item.content[0])[0], _range(item.content[-1])[1])
            for item in inner.content
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
        DraftExists: the source has changed since it was frozen, or the markdown would
            overwrite a file that no draft claims. Neither happens with `start_over`.
    """
    _require_conversion_tools()
    source = Path(file)
    markdown = (
        source.read_bytes()
        if file_type(file) == "markdown"
        else _pandoc(file, _MARKDOWN).encode("utf-8")
    )
    frozen = source if file_type(file) == "markdown" else source.with_suffix(".md")
    draft = source.parent / DRAFT
    digest = f"sha256:{hashlib.sha256(markdown).hexdigest()}"

    if not start_over:
        if draft.is_file():
            if json.loads(draft.read_text(encoding="utf-8"))["hash"] != digest:
                raise DraftExists(
                    f"{source.name} has changed since {DRAFT} was written from it. "
                    "Run in2lambda source add --start-over to freeze it again, which "
                    "invalidates every line range taken from the old draft."
                )
        elif frozen != source and frozen.exists():
            raise DraftExists(
                f"{frozen.name} is already there and no {DRAFT} claims it, so it is "
                "not ours to overwrite. Move it aside, or run in2lambda source add "
                "--start-over."
            )

    if frozen != source:
        frozen.write_bytes(markdown)
    draft.write_text(
        json.dumps(
            {
                "source": frozen.name,
                "hash": digest,
                "blocks": [
                    block.to_dict() for block in blocks(markdown.decode("utf-8"))
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
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
    """
    draft_path = Path(directory) / DRAFT
    if not draft_path.is_file():
        raise DraftMissing(
            f"There is no {DRAFT} in {draft_path.parent.resolve()}. "
            "Run in2lambda source add FILE first."
        )
    draft = json.loads(draft_path.read_text(encoding="utf-8"))

    ids = {block["start"]: block["id"] for block in draft["blocks"]}
    lines = (
        (draft_path.parent / draft["source"]).read_text(encoding="utf-8").splitlines()
    )
    margin = max((len(block_id) for block_id in ids.values()), default=0)
    numbers = len(str(len(lines)))
    return "\n".join(
        f"{ids.get(number, ''):>{margin}}  {number:>{numbers}}  {line}".rstrip()
        for number, line in enumerate(lines, start=1)
    )
