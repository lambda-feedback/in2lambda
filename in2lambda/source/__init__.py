"""Freezes the source documents of a draft, so that their text can be quoted by line range.

A tool that writes questions from a document copies the wording out of the source, and a
line range identifies that wording only while the text does not change. So in2lambda
freezes the document once: :func:`add` converts it to markdown, hashes the markdown, and
writes a ``FILE.draft.json`` beside it listing every top-level block with the lines that
block spans.

The draft is named after the source it was frozen from, so a folder holding a term's
sheets holds one draft per sheet.

A draft freezes several documents where a sheet is written as several files, such as the
questions in one file and the solutions in another. The sources are numbered in the order
they were frozen, and a block id or a line range of any source after the first carries
that source's number: ``2/b3``, ``2/s10:14``. The first source's ids and ranges are
written plain.

Every function here needs pandoc, and the parsing needs panflute, which only the
``convert`` extra installs. :func:`add` raises :class:`ConversionToolsMissing` naming what
to install.
"""

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DRAFT_SUFFIX = ".draft.json"
"""The suffix of a draft, which is written beside its source and named after it."""


def _field_fault(field: Any) -> str:
    """What is wrong with the shape of one field of a draft, or "" if nothing is wrong.

    A field is checked for ``ranges``, ``source`` and ``value``, because those are the
    parts of a field this package reads: `in2lambda.draft.record` compares the lines a
    command is quoting against the lines every field of that source was taken from, and
    `in2lambda.draft.report.checks` reports a field holding an empty value. The check
    asks only whether a value is present, because the checks read a value as a string or
    not at all. The layer, the edited flag and the editor are written and read back
    whole, and `in2lambda draft replay` catches an edit to any of them byte for byte.

    A field quoted from the first source holds no ``source`` key, as every field of a
    draft frozen from one document does.
    """
    if not isinstance(field, dict):
        return "is not an object"
    if not isinstance(field.get("source", 1), int):
        return f"has source {field['source']!r} rather than a number"
    if "ranges" not in field:
        return "has no ranges"
    if not isinstance(field["ranges"], list) or not all(
        isinstance(pair, list)
        and len(pair) == 2
        and all(isinstance(line, int) for line in pair)
        for pair in field["ranges"]
    ):
        return f"has ranges {field['ranges']!r} rather than pairs of line numbers"
    if "value" not in field:
        return "has no value"
    return ""


_FIELDS = ("sources", "log", "fields")
"""The keys a draft holds, and so the keys a file must hold to be read as a draft.

``sources`` holds one ``{source, hash, blocks}`` per frozen document, in the order they
were frozen. A draft written before a draft could hold more than one source holds those
three keys at the top level, and is refused as a draft in2lambda did not write: its ids
and ranges were written against a shape this package no longer reads. The refusal says to
freeze the document again.

A draft written before ``log`` and ``fields`` existed holds neither, and is refused as a
draft in2lambda did not write: there is no command log to replay it from, and an empty log
would claim its fields came from nowhere. The refusal says to freeze the source again.

A draft that `in2lambda validate` has been run on also holds a ``report``, which is not
required and not checked: nothing here reads a report back, and the next run of the checks
writes over it.
"""

_MARKDOWN = "commonmark_x"
"""The dialect the frozen markdown is written in, and read back as.

The writer and the reader must agree. Pandoc's ``markdown`` writer emits fenced divs and
bracketed spans that a commonmark reader reads as ordinary text. ``commonmark_x`` also
covers the ``$...$`` maths and the ``{width=...}`` attributes a converted document holds.
"""

_POSITION = re.compile(r"(?:[^@;]*@)?(\d+):\d+-(\d+):(\d+)")
"""One ``line:column-line:column`` of a ``data-pos``, which may name a file and repeat."""


class SourceError(RuntimeError):
    """Freezing or printing a source failed, for a reason worth printing.

    The command line prints the message of any of these and exits non-zero. A fault a
    reader can act on, such as a draft another tool wrote or a file that has moved, is
    raised as one of these.
    """


class ConversionToolsMissing(SourceError):
    """Document conversion was asked for without pandoc or panflute installed."""


class DraftExists(SourceError):
    """A draft is already there and was not written from this version of the source."""


class DraftMissing(SourceError):
    """There is no draft at the path a command looked in."""


class ManyDrafts(SourceError):
    """A directory holds more than one draft, so the command cannot choose one."""


class DraftUnreadable(SourceError):
    """A file is where the draft goes, and that file is not a draft."""


class SourceUnreadable(SourceError):
    """The markdown to read has moved, or is not UTF-8 text."""


def draft_of(source: str | Path) -> Path:
    """Where the draft of a document goes, which is beside it and named after it.

    Args:
        source: The document that was or would be frozen, in any format :func:`add`
            takes. A draft's own path is returned unchanged, so that a command reading a
            path from a reader accepts either.

    Returns:
        The path of that document's draft.

    Examples:
        >>> from in2lambda.source import draft_of
        >>> draft_of("sheets/week1.tex").name
        'week1.draft.json'
        >>> draft_of("sheets/week1.draft.json").name
        'week1.draft.json'
    """
    path = Path(source)
    if path.name.endswith(DRAFT_SUFFIX):
        return path
    return path.with_name(f"{path.stem}{DRAFT_SUFFIX}")


def find(given: Optional[str] = None, directory: str = ".") -> Path:
    """The draft a command was asked to work on, or the one draft in a directory.

    Args:
        given: The draft a reader named, as the draft's path or as the path of the
            source it was frozen from. None reads `directory` instead.
        directory: Where to look when the reader named no draft.

    Returns:
        The path of the draft to read.

    Raises:
        DraftMissing: the reader named no draft and `directory` holds none.
        ManyDrafts: the reader named no draft and `directory` holds several.
    """
    if given is not None:
        return draft_of(given)
    found = sorted(Path(directory).glob(f"*{DRAFT_SUFFIX}"))
    if len(found) == 1:
        return found[0]
    where = Path(directory).resolve()
    if not found:
        raise DraftMissing(
            f"There is no draft in {where}. Run in2lambda source add FILE first."
        )
    raise ManyDrafts(
        f"There is more than one draft in {where}: "
        f"{', '.join(path.name for path in found)}. Name one with --draft."
    )


def _require_conversion_tools() -> None:
    missing = []
    if shutil.which("pandoc") is None:
        missing.append("pandoc (see https://pandoc.org/installing.html)")
    # panflute and pyyaml come from the one extra, so one hint names both packages.
    if absent := [
        package
        for module, package in (("panflute", "panflute"), ("yaml", "pyyaml"))
        if importlib.util.find_spec(module) is None
    ]:
        missing.append(f"{' and '.join(absent)} (pip install 'in2lambda[convert]')")
    if missing:
        raise ConversionToolsMissing(
            f"Converting documents needs {' and '.join(missing)}."
        )


def file_type(file: str) -> str:
    """The pandoc input format for a file, read from the file's extension.

    See https://github.com/jgm/pandoc/blob/bad922a69236e22b20d51c4ec0b90c5a6c038433/src/Text/Pandoc/Format.hs#L171
    (or any newer commit) for the extensions pandoc supports.

    Args:
        file: A file path, including the file extension.

    Returns:
        The option of `pandoc --list-input-formats` that matches the extension.

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
            return "docx"  # Pandoc reads no .doc, and panflute does not read .docx.
    raise RuntimeError(f"Unsupported file extension: .{extension}")


def _pandoc(file: str, to: str) -> bytes:
    """The given file, as pandoc writes it in the `to` format.

    The bytes are returned undecoded, because the file written to disk and the bytes
    hashed must be the same. A caller wanting the text decodes them.
    """
    return subprocess.check_output(["pandoc", file, "-f", file_type(file), "-t", to])


def _digest(data: bytes) -> str:
    """How a frozen markdown is named in its draft, so that a change to it is reported.

    The digest is of the bytes of the file, not of the text they decode to: whoever
    quotes the markdown checks the draft against the file alone, and `sha256sum` on that
    file must give the same answer whatever line endings the file holds.
    """
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _source(path: Path) -> tuple[bytes, str]:
    """A markdown file as bytes and as text, where the file is present and is text.

    Both freezing and showing read a markdown file, and a reader who has moved the file
    or saved it in another encoding is told which fault occurred. The bytes are what
    :func:`_digest` hashes, and `bytes.decode` rewrites no line endings, so the text
    holds the line endings the file holds.
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
    """The draft at the given path, where in2lambda wrote it.

    Raises:
        DraftMissing: there is no file at that path.
        DraftUnreadable: the file is not JSON, or is not a draft. in2lambda neither
            reads from nor writes over such a file.
    """
    if not path.is_file():
        raise DraftMissing(
            f"There is no {path.resolve()}. Run in2lambda source add FILE first."
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
            f"{path} is not a draft in2lambda wrote: it holds no "
            f"{' or '.join(missing)}. {advice}"
        )
    # Every read of a draft passes through here, so a hand-edited log or fields is
    # refused with a message instead of a TypeError from the code that iterates it.
    for field, shape, called in (
        ("sources", list, "a list"),
        ("log", list, "a list"),
        ("fields", dict, "an object"),
    ):
        if not isinstance(draft[field], shape):
            raise DraftUnreadable(
                f"{path} is not a draft in2lambda wrote: its {field} is "
                f"{draft[field]!r} rather than {called}. {advice}"
            )
    if not draft["sources"]:
        # `add` freezes a file or refuses, so in2lambda writes no empty list. A draft
        # holding one has been edited by hand, and every id and range in it names a
        # document that is no longer frozen. The rest of this package reads the first
        # source as the one an unqualified id belongs to.
        raise DraftUnreadable(
            f"{path} is not a draft in2lambda wrote: its sources is empty, so it names "
            f"no frozen document for its fields to have been quoted out of. {advice}"
        )
    for source in draft["sources"]:
        if not isinstance(source, dict) or not all(
            key in source for key in ("source", "hash", "blocks")
        ):
            raise DraftUnreadable(
                f"{path} is not a draft in2lambda wrote: its sources holds "
                f"{source!r} rather than a frozen document, its hash and its blocks. "
                f"{advice}"
            )
    for key, field in draft["fields"].items():
        if fault := _field_fault(field):
            raise DraftUnreadable(
                f"{path} is not a draft in2lambda wrote: its fields holds {key}, which "
                f"{fault}. {advice}"
            )
    return draft


def serialise(draft: dict[str, Any]) -> bytes:
    """The bytes a draft is written as, which is the only form a draft is written in.

    The keys are sorted and the result is bytes, so that the same draft is the same
    file. `in2lambda draft replay` reproduces a draft byte for byte, which fails if the
    key order follows the order the keys were written in, or if the newlines follow the
    machine that wrote them.
    """
    return (json.dumps(draft, indent=2, sort_keys=True) + "\n").encode("utf-8")


def save(path: Path, draft: dict[str, Any]) -> None:
    """Writes a draft to the given path."""
    path.write_bytes(serialise(draft))


def frozen(draft: str | Path) -> tuple[dict[str, Any], list[str]]:
    """A draft and the markdown of every source it names, where no source has changed.

    Args:
        draft: The path of the draft to read.

    Returns:
        The draft, and the text of each markdown it names, in the order it froze them.
        The first is source 1, whose blocks and lines are named unqualified.

    Raises:
        DraftMissing: there is no draft at that path.
        DraftUnreadable: the file at that path is not a draft in2lambda wrote.
        SourceUnreadable: a markdown the draft names has moved, or is not text.
        DraftExists: a markdown has changed since the draft was written from it, so the
            line ranges in the draft no longer name the lines they were taken from. The
            message names the file that changed, because a draft may hold several.
    """
    path = Path(draft)
    found = _draft(path)
    texts = []
    for source in found["sources"]:
        raw, markdown = _source(path.parent / source["source"])
        if _digest(raw) != source["hash"]:
            raise DraftExists(
                f"{source['source']} has changed since {path.name} was written from "
                "it, so its block ids no longer name the lines they were written "
                "against. Run in2lambda source add --start-over to freeze the file as "
                "it now is."
            )
        texts.append(markdown)
    return found, texts


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
        """The block as it is written into the draft."""
        return {"id": self.id, "type": self.type, "start": self.start, "end": self.end}


def _numbered(source: int, name: str) -> str:
    """A block id or a line range as the source it names writes it.

    The first source writes them plain - ``b3``, ``s10:14`` - as every draft did when a
    draft held one source. Every source after it prefixes its number and a slash, so
    that an id or a range names the document it belongs to.
    """
    return name if source == 1 else f"{source}/{name}"


def blocks(markdown: str, source: int = 1) -> list[Block]:
    r"""Every top-level block of some markdown, in the order it is written.

    Args:
        markdown: A document in the dialect :func:`add` freezes to.
        source: Which source of a draft the markdown is, which numbers the ids of any
            but the first: a draft's second source has ``2/b1``, ``2/b2``.

    Returns:
        One :class:`Block` per block, numbered ``b1`` onwards. The blocks do not
        overlap, and every line of the document falls in at most one block. A block of a
        type no command quotes is listed as ``other``, so that its lines have an id.

    Examples:
        >>> from in2lambda.source import blocks
        >>> blocks("# Title\n\nSome words.\n")
        [Block(id='b1', type='heading', start=1, end=1), Block(id='b2', type='paragraph', start=3, end=3)]
        >>> [block.id for block in blocks("# Solutions\n", 2)]
        ['2/b1']
    """
    return [block for block, _ in _elements(markdown, source)]


_MARKER = re.compile(r" *(?:[-+*]|\(?(?:\d+|[ivxlcdm]+|[IVXLCDM]+|[A-Za-z])[.)]) {1,4}")
"""A list item's marker on its first line, as `commonmark_x` reads one."""


def dedented(text: str) -> str:
    r"""Some lines of a list item, with the item's own indentation off every one.

    A field quoted out of a list item would otherwise hold the marker and the
    continuation indent the markdown needs, and four leading spaces after a blank line
    render as a code block.

    Args:
        text: The lines as the source writes them, the first holding the item's marker.

    Returns:
        The same lines, with the marker off the first line and as much of the same width
        off each line below as that line has to give, so that a list nested inside the
        item keeps its relative indent. Text whose first line holds no marker is returned
        unchanged. A paragraph that reads like a marker - ``A. Smith says`` - would be
        dedented, so the caller decides by the block's type and not by its text.

    Examples:
        >>> from in2lambda.source import dedented
        >>> dedented("1.  A person walks\n    to the edge.")
        'A person walks\nto the edge.'
        >>> dedented("    (a) Find the speed\n        afterwards.")
        'Find the speed\nafterwards.'
        >>> dedented("Some words\n  wrapped.")
        'Some words\n  wrapped.'
    """
    if (marker := _MARKER.match(text)) is None:
        return text
    width = marker.end()
    first, *rest = text.split("\n")
    return "\n".join(
        [first[width:]]
        + [line[min(width, len(line) - len(line.lstrip(" "))) :] for line in rest]
    )


def _elements(markdown: str, source: int = 1) -> list[tuple[Block, Any]]:
    """Every block of some markdown, each beside the panflute element it was taken from.

    A selector matches on the element's type, its heading level and the text it
    stringifies to, none of which a block records, so code matching against the source
    calls this and projects the blocks out of the result, as :func:`blocks` does.
    """
    import panflute as pf

    document = pf.convert_text(
        markdown, input_format=f"{_MARKDOWN}+sourcepos", standalone=True
    )
    found = [span for element in document.content for span in _spans(element, pf)]
    # Where no blank line separates one block from the next - a list straight after a
    # paragraph, a definition list - pandoc reports the first block as reaching into the
    # second block's first line. So a block ends before the next block starts, and
    # before the end of the document.
    limits = [start - 1 for _, start, _, _ in found[1:]] + [len(markdown.splitlines())]
    return [
        (Block(_numbered(source, f"b{number}"), kind, start, min(end, limit)), element)
        for number, ((kind, start, end, element), limit) in enumerate(
            zip(found, limits), 1
        )
    ]


def _spans(element, pf):  # type: ignore[no-untyped-def]
    """The ``(type, start, end, element)`` quadruples one top-level element accounts for.

    A list accounts for several: a command quotes a list item, not a list, and an item
    spans everything nested under it. The element returned is the block itself, past the
    Div `sourcepos` wraps it in, so that a selector matches the element an author would
    name.
    """
    inner = _unwrapped(element, pf)
    if isinstance(inner, (pf.BulletList, pf.OrderedList)):
        # An empty item - a lone bullet, which a .docx often holds - carries no element
        # with a position, so it has no range and is left out.
        return [
            ("list item", _range(item.content[0])[0], _range(item.content[-1])[1], item)
            for item in inner.content
            if len(item.content)
        ]
    return [(_kind(inner, pf), *_range(element), inner)]


def _unwrapped(element, pf):  # type: ignore[no-untyped-def]
    """An element, past the Div that `sourcepos` wraps it in.

    Only elements that take attributes of their own, such as a heading or a table, carry
    ``data-pos`` directly. Pandoc wraps every other element in a Div to hang ``data-pos``
    on.
    """
    if isinstance(element, pf.Div) and element.attributes.get("wrapper"):
        return element.content[0]
    return element


def _kind(inner, pf) -> str:  # type: ignore[no-untyped-def]
    """The :class:`Block` type an unwrapped element is."""
    if isinstance(inner, pf.Header):
        return "heading"
    if isinstance(inner, (pf.Para, pf.Plain)):
        # A paragraph holding one image, or one $$...$$, and nothing else is typed as
        # that element.
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

    An element may carry more than one position, one per part of the element, and the
    whole element is wanted. An end at column 1 means the block stopped before that
    line, which is how pandoc reports every block that ends in a newline.
    """
    positions = _POSITION.findall(element.attributes["data-pos"])
    return (
        min(int(start) for start, _, _ in positions),
        max(
            int(end) - 1 if column == "1" else int(end) for _, end, column in positions
        ),
    )


def add(
    files: list[str], start_over: bool = False, into: str | Path | None = None
) -> Path:
    """Freezes one or more documents and writes the draft of them beside the files.

    A .docx or .tex file is converted to markdown beside it. A markdown file is frozen
    as it stands and nothing is copied. Either way the markdown is hashed and its blocks
    are written to ``FILE.draft.json``, so that code quoting a source by line range can
    check that those lines still hold the text they held.

    The files are numbered in the order they are given. A file already frozen into the
    draft beside them is checked against the hash it was frozen at, and is not frozen
    again. So a sheet and the solutions written separately are frozen together, or the
    solutions added later as the next source, and the questions keep the ids and the
    lines the commands so far were run against.

    Args:
        files: The documents to freeze, as .docx, .tex or markdown, all in the one
            directory, in the order they are to be numbered in.
        start_over: Freeze the files again, discarding the draft already there.
        into: The draft to freeze the files into, as the draft's path or as the path of
            a source already in it. None names the draft after the first file. A file
            frozen into a draft already written becomes a source of that draft.

    Returns:
        The path of the draft that was written.

    Raises:
        ConversionToolsMissing: pandoc or panflute is not installed.
        SourceError: the files are not all in one directory, so no one draft sits
            beside them.
        SourceUnreadable: a file is markdown, and is not UTF-8 text.
        DraftUnreadable: a draft beside the files is not a draft in2lambda wrote, so
            this function neither reads a hash out of it nor writes over it.
        DraftExists: a source has changed since it was frozen, or a markdown would
            overwrite a file that no draft claims. `start_over` overrides both.
    """
    _require_conversion_tools()
    paths = [Path(file) for file in files]
    if len({path.parent for path in paths}) != 1:
        raise SourceError(
            "A draft sits beside the documents it was frozen from, so the files frozen "
            f"into one draft are all in the same directory: {', '.join(files)}."
        )
    draft = draft_of(paths[0] if into is None else into)

    # A draft already here holds the commands run against it, which freezing the same
    # files again does not undo: those commands were run against these lines, so they
    # still hold. The blocks are kept for the same reason, and parsing the markdown does
    # not always give them: `split block` cuts a block in two, and parsing again would
    # undo that cut while keeping the log entry recording it, leaving the ids the fields
    # were written against naming nothing. --start-over is the only way to discard them.
    existing: dict[str, Any] = {"sources": [], "log": [], "fields": {}}
    if not start_over and draft.is_file():
        existing = _draft(draft)
    sources: list[dict[str, Any]] = list(existing["sources"])

    # Every file is read and parsed before any file is written: a parse that fails part
    # way through would otherwise leave a markdown on disk that no draft claims, and the
    # next run would refuse to overwrite a file this run wrote.
    converted: list[tuple[Path, bytes]] = []
    for path in paths:
        if file_type(str(path)) == "markdown":
            raw, markdown = _source(path)
            frozen_path = path
        else:
            raw = _pandoc(str(path), _MARKDOWN)
            markdown = raw.decode("utf-8")
            frozen_path = path.with_suffix(".md")
            converted.append((frozen_path, raw))
        digest = _digest(raw)
        if found := next(
            (source for source in sources if source["source"] == frozen_path.name), None
        ):
            if found["hash"] != digest:
                raise DraftExists(
                    f"{path.name} has changed since {draft.name} was written from it. "
                    "Run in2lambda source add --start-over to freeze it again, which "
                    "invalidates every line range taken from the old draft."
                )
            continue
        if not start_over and frozen_path != path and frozen_path.exists():
            raise DraftExists(
                f"{frozen_path.name} is already there and no {draft.name} claims it, "
                "so in2lambda does not overwrite it. Move it aside, or run in2lambda "
                "source add --start-over."
            )
        sources.append(
            {
                "source": frozen_path.name,
                "hash": digest,
                "blocks": [
                    block.to_dict() for block in blocks(markdown, len(sources) + 1)
                ],
            }
        )

    for frozen_path, raw in converted:
        # The bytes pandoc wrote, so that the file on disk hashes to `digest`. Writing
        # text would rewrite the line endings on Windows.
        frozen_path.write_bytes(raw)
    # Freezing starts a draft and is not recorded in the log: a replay applies the log
    # to what `add` wrote, so `add` writes no log entry of its own.
    save(
        draft,
        {
            "sources": sources,
            "log": existing["log"],
            "fields": existing["fields"],
            # The report still describes the draft where every file named was frozen
            # already, because `add` then writes the draft back unchanged. An appended
            # source is a document the checks have never read, and every block of it is
            # in no field, so the report is deleted as any change to a draft deletes it.
            # `in2lambda build` then asks for the checks again.
            **(
                {"report": existing["report"]}
                if existing.get("report") is not None and sources == existing["sources"]
                else {}
            ),
        },
    )
    return draft


def show(draft: str | Path) -> str:
    """The frozen markdown of a draft, numbered, with block ids in the margin.

    Args:
        draft: The path of the draft to print.

    Returns:
        One line per line of each frozen markdown: the id of the block starting there,
        where a block starts there, then the line number and the line itself. A draft of
        more than one source heads each source with its number and its name, because the
        line numbers start again at 1 in each source.

    Raises:
        DraftMissing: there is no draft at that path.
        DraftUnreadable: the file at that path is not a draft in2lambda wrote.
        SourceUnreadable: a markdown the draft names has moved, or is not text.
        DraftExists: a markdown has changed since the draft was written from it, so
            the ids would be printed against lines they were not taken from.
    """
    # A line range identifies text only while that text does not change: ids printed
    # against markdown the draft was not written from would look right and be wrong.
    found, sources = frozen(draft)

    printed = []
    for number, (source, markdown) in enumerate(
        zip(found["sources"], sources), start=1
    ):
        ids = {block["start"]: block["id"] for block in source["blocks"]}
        lines = markdown.splitlines()
        margin = max((len(block_id) for block_id in ids.values()), default=0)
        numbers = len(str(len(lines)))
        body = "\n".join(
            f"{ids.get(line_number, ''):>{margin}}  {line_number:>{numbers}}  {line}".rstrip()
            for line_number, line in enumerate(lines, start=1)
        )
        printed.append(
            f"Source {number}: {source['source']}\n{body}" if len(sources) > 1 else body
        )
    return "\n\n".join(printed)
