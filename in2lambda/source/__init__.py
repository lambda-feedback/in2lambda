"""Freezes the source documents of a draft, so their text can be quoted by line range.

Anything that writes questions from a document - the in2lambda agent, say - needs to
take the wording out of the source rather than retype it, and a line range is only an
address if the text it points into cannot move underneath it. So the document is frozen
once: converted to markdown, hashed, and written down beside a ``FILE.draft.json``
listing every top-level block with the lines it spans.

The draft is named after the source it was frozen from, so a folder holding a term's
worth of sheets holds a draft for each rather than one they take turns overwriting.

A draft freezes several documents where a sheet is written that way - the questions in
one file and the solutions in another. They are numbered in the order they were frozen,
and a block id or a line range of any source after the first carries its number:
``2/b3``, ``2/s10:14``. The first source's are written plain, as they were when a draft
held one.

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
from typing import Any, Optional

DRAFT_SUFFIX = ".draft.json"
"""What a frozen source is written to, beside the source itself and named after it."""


def _field_fault(field: Any) -> str:
    """What is wrong with the shape of one field of a draft, or "" if nothing is.

    ``ranges``, ``source`` and ``value`` are what is looked for, because they are the
    parts of a field anything here reads: `in2lambda.draft.record` compares the lines a
    command is quoting against the lines every field of that source was taken from, and
    `in2lambda.draft.report.checks` reports a field whose value says nothing. Only
    whether there is a value is asked, since the checks look at one as a string or not
    at all. The layer, whether it was edited and by whom are written and read back
    whole, and an edit to any of them is what a replay catches byte for byte.

    A field quoted from the first source has no ``source`` in it, which is what every
    field of a draft frozen from one document looks like.
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
"""What a draft has in it, and so what one has to have for anything here to read it.

``sources`` is one ``{source, hash, blocks}`` per frozen document, in the order they
were frozen. A draft written before there could be more than one holds those three at
the top level instead, and is refused as one nothing here wrote rather than read as a
draft of one source: the ids and ranges in it were written against a shape that has
gone. Freezing the document again is the way through, which is what the refusal says.

A draft written before ``log`` and ``fields`` existed has neither, and is refused as one
nothing here wrote: there is no command log to replay it from, and inventing an empty one
would claim the fields in it came from nowhere. Freezing the source again is the way
through, which is what the refusal says.

A draft `in2lambda validate` has been run on also has a ``report``, which is not required
and not looked into: nothing here reads one back, and the next run of the checks writes
whatever is there over.
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
    """There is no draft where one was looked for."""


class ManyDrafts(SourceError):
    """A directory holds more than one draft, so which was meant has to be said."""


class DraftUnreadable(SourceError):
    """There is a file where the draft goes, but it is not a draft."""


class SourceUnreadable(SourceError):
    """The markdown to read has moved, or is not text."""


def draft_of(source: str | Path) -> Path:
    """Where the draft of a document goes, which is beside it and named after it.

    Args:
        source: The document that was or would be frozen, in any format :func:`add`
            takes. A draft's own path is given back as it is, so that anything taking
            one from a reader can take either.

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
    """Which draft a command was asked to work on, or the one draft there is.

    Args:
        given: What a reader named, as the draft or as the source it was frozen from,
            or nothing to go by what is in `directory`.
        directory: Where to look when nothing was named.

    Returns:
        The path of the draft to read.

    Raises:
        DraftMissing: nothing was named and there is no draft to fall back on.
        ManyDrafts: nothing was named and there is more than one, so a folder of
            sheets does not silently act on whichever sorts first.
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
        f"{', '.join(path.name for path in found)}. Say which with --draft."
    )


def _require_conversion_tools() -> None:
    missing = []
    if shutil.which("pandoc") is None:
        missing.append("pandoc (see https://pandoc.org/installing.html)")
    # Both come from the one extra, so they are named together rather than twice over.
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


def _pandoc(file: str, to: str, *options: str) -> bytes:
    """The given file, as pandoc writes it in the `to` format.

    Undecoded, because what is written to disk and what is hashed have to be the same
    bytes; whoever wants the text of it decodes it themselves.
    """
    return subprocess.check_output(
        ["pandoc", file, "-f", file_type(file), "-t", to, *options]
    )


_DISPLAY_MATHS = re.compile(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$", re.DOTALL)
"""Display maths as ``commonmark_x`` writes it: opened and closed on the one line."""

_MARKER = re.compile(r" *(?:[-+*]|\(?(?:\d+|[ivxlcdm]+|[IVXLCDM]+|[A-Za-z])[.)]) {1,4}")
"""A list item's marker on its first line, as `commonmark_x` reads one."""


def _verbatim_lines(markdown: str) -> set[int]:
    r"""The lines of some markdown whose ``$$`` is code rather than maths.

    ``commonmark_x`` fences a code block that carries a language and indents one that
    carries nothing four spaces, and a ``$$ ... $$`` in either is text the document
    shows rather than maths it renders. A list item's continuation paragraph is indented
    four as well, so the indent is measured from the item the line stands in rather than
    from the margin: a line four past the enclosing item's content column is code, and
    display maths standing as an item's own paragraph is maths. The column is the one
    :func:`dedented` takes off again, so a line this leaves alone is a line the field
    quoting it reads as code too.

    Examples:
        >>> from in2lambda.source import _verbatim_lines
        >>> sorted(_verbatim_lines("Text\n\n    $$x = y$$\n"))
        [3]
        >>> sorted(_verbatim_lines("1.  Item\n\n    $$x = y$$\n"))
        []
        >>> sorted(_verbatim_lines("1.  Item\n\n        $$x = y$$\n"))
        [3]
        >>> sorted(_verbatim_lines("``` python\n$$x = y$$\n```\n"))
        [1, 2, 3]
    """
    verbatim = set()
    fence = ""
    items: list[int] = []  # The content column of each list item open at this line.
    for number, line in enumerate(markdown.split("\n"), start=1):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if fence:
            verbatim.add(number)
            if stripped.startswith(fence):
                fence = ""
        elif not stripped:
            # Commonmark closes an item at the next non-blank line indented less than
            # its content column, not at the blank line before that one.
            continue
        else:
            while items and indent < items[-1]:
                items.pop()
            base = items[-1] if items else 0
            if stripped[:3] in ("```", "~~~"):
                fence = stripped[:3]
                verbatim.add(number)
            elif indent >= base + 4:
                verbatim.add(number)
            elif marker := _MARKER.match(line):
                items.append(marker.end())
    return verbatim


def _display_maths_blocked(markdown: str) -> str:
    r"""Markdown pandoc wrote, with its display maths moved onto lines of its own.

    ``commonmark_x`` writes ``$$F = p A$$`` on one line wherever in a paragraph the
    maths stood, which is the one form the delimiter checks refuse and no real Lambda
    Feedback export uses. Rewriting it at the freeze rather than at the field is what
    makes every range quoted out of the markdown render, however the maths was written.

    The inserted lines take the indent of the line the maths began on - a list item's
    marker width included, so maths in an item stays in the item - and whatever stood
    either side of it on that line becomes a paragraph of its own.

    A ``$$`` that opens or closes on a pipe table's row, on a block quote's line or on a
    code block's line is left as pandoc wrote it: a table cell cannot hold a block, an
    inserted line carries the indent of the opening line but not a quote's ``> ``, and a
    code block's ``$$`` is characters the document shows. A match running across a blank
    line is left as written as well, since display maths holds no blank line: such a
    match is an unpaired ``$$`` - one in inline code, say - closed by the opening ``$$``
    of a later maths, and that later maths is then left as written too.
    ``in2lambda validate`` reports the maths left in any of these.

    Examples:
        >>> from in2lambda.source import _display_maths_blocked
        >>> _display_maths_blocked("The load is $$F = pA$$ here.\n")
        'The load is\n\n$$\nF = pA\n$$\n\nhere.\n'
        >>> _display_maths_blocked("1.  Find $$F = pA$$\n")
        '1.  Find\n\n    $$\n    F = pA\n    $$\n'
        >>> _display_maths_blocked("A load $$F = pA$$\r\n")
        'A load\r\n\r\n$$\r\nF = pA\r\n$$\r\n'
        >>> _display_maths_blocked("> The load is $$F = pA$$ here.\n")
        '> The load is $$F = pA$$ here.\n'
        >>> _display_maths_blocked("Type this:\n\n    $$x = y$$\n")
        'Type this:\n\n    $$x = y$$\n'
        >>> _display_maths_blocked("``` python\nprint(\"$$x = y$$\")\n```\n")
        '``` python\nprint("$$x = y$$")\n```\n'
        >>> _display_maths_blocked("Type `$$` first.\n\nThe load is $$F = pA$$\n")
        'Type `$$` first.\n\nThe load is $$F = pA$$\n'
        >>> _display_maths_blocked("The load is $$F = pA\n> and $$ here.\n")
        'The load is $$F = pA\n> and $$ here.\n'
    """
    if "\r\n" in markdown:
        # Pandoc writes the line endings of whoever is running it, and the file on disk
        # is hashed as it is written, so a Windows freeze stays a Windows file.
        blocked = _display_maths_blocked(markdown.replace("\r\n", "\n"))
        return blocked.replace("\n", "\r\n")

    verbatim = _verbatim_lines(markdown)

    def blocked(position: int) -> bool:
        """Whether the `$$` at this offset stands in a table row, a quote or code."""
        opening = markdown[markdown.rfind("\n", 0, position) + 1 : position]
        return opening.lstrip()[:1] in ("|", ">") or (
            markdown.count("\n", 0, position) + 1 in verbatim
        )

    written: list[str] = []
    end = 0
    for match in _DISPLAY_MATHS.finditer(markdown):
        if any(not line.strip() for line in match.group().split("\n")):
            # Display maths holds no blank line, so a match across one is an unpaired
            # `$$` closed by the opening `$$` of a later maths. Rewriting it would make
            # a maths block of the paragraphs standing between the two.
            continue
        if blocked(match.start()) or blocked(match.end()):
            # A pipe table's cell cannot hold a block; an inserted line carries the
            # indent of the line the maths began on but not a block quote's `> `, so the
            # rewrite would put the maths and the words after it outside the quote; and
            # a code block's `$$` is characters the document shows, not maths. Either
            # delimiter standing in one of the three is enough to leave the match alone.
            continue
        before = markdown[markdown.rfind("\n", 0, match.start()) + 1 : match.start()]
        marker = _MARKER.match(before)
        indent = " " * (
            marker.end() if marker else len(before) - len(before.lstrip(" "))
        )
        # Maths that already starts its line - or the line's list item - needs no break
        # before it, and the indent it would be given is in the line already.
        opens_the_line = not before.strip() or (
            marker is not None and marker.end() == len(before)
        )
        head = markdown[end : match.start()]
        written.append(head if opens_the_line else f"{head.rstrip(' ')}\n\n{indent}")
        body = "\n".join(
            f"{indent}{line.strip()}" for line in match.group(1).strip().split("\n")
        )
        written.append(f"$$\n{body}\n{indent}$$")
        end = match.end()
        rest = markdown[end:].split("\n", 1)[0]
        if rest.strip():
            written.append(f"\n\n{indent}")
            end += len(rest) - len(rest.lstrip(" "))
    written.append(markdown[end:])
    return "".join(written)


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
            f"{path} is not a draft anything here wrote: it has no "
            f"{' or '.join(missing)} in it. {advice}"
        )
    # The one gate everything reading a draft passes through, so a hand-edited log or
    # fields is refused here rather than as a TypeError from whatever iterated it.
    for field, shape, called in (
        ("sources", list, "a list"),
        ("log", list, "a list"),
        ("fields", dict, "an object"),
    ):
        if not isinstance(draft[field], shape):
            raise DraftUnreadable(
                f"{path} is not a draft anything here wrote: its {field} is "
                f"{draft[field]!r} rather than {called}. {advice}"
            )
    if not draft["sources"]:
        # Nothing here writes one: `add` freezes a file or refuses. So an empty list is
        # a hand-edited draft, and every id and range in it names a document that is no
        # longer there - which is what the rest of this package would trip over rather
        # than report, since it takes the first source as the one an unqualified id is
        # of.
        raise DraftUnreadable(
            f"{path} is not a draft anything here wrote: its sources is empty, so "
            f"there is no frozen document for its fields to have been quoted out of. "
            f"{advice}"
        )
    for source in draft["sources"]:
        if not isinstance(source, dict) or not all(
            key in source for key in ("source", "hash", "blocks")
        ):
            raise DraftUnreadable(
                f"{path} is not a draft anything here wrote: its sources holds "
                f"{source!r} rather than a frozen document, its hash and its blocks. "
                f"{advice}"
            )
    for key, field in draft["fields"].items():
        if fault := _field_fault(field):
            raise DraftUnreadable(
                f"{path} is not a draft anything here wrote: its fields has {key} "
                f"that {fault}. {advice}"
            )
    return draft


def serialise(draft: dict[str, Any]) -> bytes:
    """The bytes a draft is written as, which is the only form it is ever written in.

    Sorted, and bytes rather than text, so that the same draft is the same file:
    replaying a command log has to reproduce the draft exactly, which it cannot do
    if the key order depends on what order something happened to write the keys in, or
    if the newlines depend on which machine wrote them.
    """
    return (json.dumps(draft, indent=2, sort_keys=True) + "\n").encode("utf-8")


def save(path: Path, draft: dict[str, Any]) -> None:
    """Writes a draft to the given path."""
    path.write_bytes(serialise(draft))


def frozen(draft: str | Path) -> tuple[dict[str, Any], list[str]]:
    """A draft and the markdown of every source it names, still unmoved.

    Args:
        draft: The path of the draft to read.

    Returns:
        The draft, and the text of each markdown it names, in the order it froze them:
        the first is source 1, whose blocks and lines are the ones named unqualified.

    Raises:
        DraftMissing: there is no draft at that path.
        DraftUnreadable: what is there is not a draft anything here wrote.
        SourceUnreadable: a markdown the draft names has moved, or is not text.
        DraftExists: a markdown has changed since the draft was written from it, so the
            line ranges in the draft no longer name the lines they were taken from. The
            refusal names the file that changed, since a draft may hold several.
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
    """A block id or a line range as the source it names something in writes it.

    The first source writes them plain - ``b3``, ``s10:14`` - which is what everything
    wrote when a draft held one source; every source after it puts its number and a
    slash in front, so that an id or a range says which document it is of.
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
        overlap and every line of the document falls in at most one: a block that is
        none of the types the agent quotes is still listed, as ``other``, rather than
        leaving its lines unaddressable.

    Examples:
        >>> from in2lambda.source import blocks
        >>> blocks("# Title\n\nSome words.\n")
        [Block(id='b1', type='heading', start=1, end=1), Block(id='b2', type='paragraph', start=3, end=3)]
        >>> [block.id for block in blocks("# Solutions\n", 2)]
        ['2/b1']
    """
    return [block for block, _ in _elements(markdown, source)]


def dedented(text: str) -> str:
    r"""Some lines of a list item, with the item's own indentation off every one.

    A field quoted out of a list item would otherwise carry the marker and the
    continuation indent the markdown needed to hold it together, and four leading
    spaces after a blank line are a code block wherever the field is rendered.

    Args:
        text: The lines as the source writes them, the first of them holding the
            item's marker.

    Returns:
        The same lines with the marker off the first and as much of the same width
        off each of the rest as it has to give, so that a list nested inside the item
        keeps its own relative indent. Text whose first line has no marker on it comes
        back unchanged, but a paragraph reading like one - ``A. Smith says`` - would be
        dedented, so what this is called on is decided by the block's type rather than
        by its text.

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

    A selector matches on what the element is - its type, its heading level, the text it
    stringifies to - which the block alone does not say, so anything matching against
    the source takes this and projects the blocks out of it, as :func:`blocks` does.
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
    limits = [start - 1 for _, start, _, _ in found[1:]] + [len(markdown.splitlines())]
    return [
        (Block(_numbered(source, f"b{number}"), kind, start, min(end, limit)), element)
        for number, ((kind, start, end, element), limit) in enumerate(
            zip(found, limits), 1
        )
    ]


def _spans(element, pf):  # type: ignore[no-untyped-def]
    """The ``(type, start, end, element)`` quadruples one top-level element accounts for.

    A list is several: the ticket asks for a list item, not a list, and an item spans
    everything nested under it. The element given back is the one that block is, past
    the Div `sourcepos` wraps it in, so that whatever matches on it matches on what an
    author would call it.
    """
    inner = _unwrapped(element, pf)
    if isinstance(inner, (pf.BulletList, pf.OrderedList)):
        # An item with nothing in it - a lone bullet, which a .docx often has - holds
        # no element to take a position from, so there is no range to give it and it
        # is left out rather than guessed at.
        return [
            ("list item", _range(item.content[0])[0], _range(item.content[-1])[1], item)
            for item in inner.content
            if len(item.content)
        ]
    return [(_kind(inner, pf), *_range(element), inner)]


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


def add(
    files: list[str], start_over: bool = False, into: str | Path | None = None
) -> Path:
    """Freezes one or more documents and writes the draft of them beside the files.

    A .docx or .tex file is converted to markdown next to it; a markdown file is taken
    as it is and nothing is copied. Either way the markdown is hashed and its blocks
    written to ``FILE.draft.json``, so that whatever quotes a source by line range can
    tell that the lines it was given still say what they said. A converted file is
    written unwrapped - a paragraph is one line, however long - with each ``$$ ... $$``
    on lines of its own, which is the maths Lambda Feedback renders.

    The files are numbered in the order they are given, and a file already frozen into
    the draft beside them is checked against the hash it was frozen at rather than
    frozen afresh. So a sheet and the solutions written separately from it are frozen
    together, or the solutions added later as the next source; either way the questions
    keep the ids and the lines the commands so far were run against.

    Args:
        files: The documents to freeze, as .docx, .tex or markdown, all in the one
            directory, in the order they are to be numbered in.
        start_over: Freeze them again, discarding whatever draft is already there.
        into: The draft to freeze them into, as its own path or that of a source
            already in it, and None for the one named after the first file. A file
            frozen into a draft already written is a source of that draft rather than
            the first source of one of its own.

    Returns:
        The path of the draft that was written.

    Raises:
        ConversionToolsMissing: pandoc or panflute is not installed.
        SourceError: the files are not all in one directory, so there is no one draft
            beside them to freeze them into.
        SourceUnreadable: a file is markdown, but not UTF-8 text.
        DraftUnreadable: there is a draft beside the files that nothing here wrote,
            so it is not ours to read a hash out of or to write over.
        DraftExists: a source has changed since it was frozen, or a markdown would
            overwrite a file that no draft claims. Neither happens with `start_over`.
    """
    _require_conversion_tools()
    paths = [Path(file) for file in files]
    if len({path.parent for path in paths}) != 1:
        raise SourceError(
            "A draft sits beside the documents it is of, so the files frozen into one "
            f"are all in the same directory: {', '.join(files)}."
        )
    draft = draft_of(paths[0] if into is None else into)

    # What a draft already here has been told, which freezing the same files again does
    # not undo: the commands were run against these very lines, so they still hold. The
    # blocks are kept for the same reason, and are not always what parsing the markdown
    # gives: `split block` cuts one in two, and parsing again would undo that while
    # keeping the log entry saying it happened, leaving the ids the fields were written
    # against naming nothing. --start-over is the way to throw all of it away, and the
    # only one.
    existing: dict[str, Any] = {"sources": [], "log": [], "fields": {}}
    if not start_over and draft.is_file():
        existing = _draft(draft)
    sources: list[dict[str, Any]] = list(existing["sources"])

    # Every file is read and parsed before any is written: a parse that fails half way
    # through would otherwise leave a markdown there with no draft claiming it, and the
    # next run would refuse to touch a file this one wrote.
    converted: list[tuple[Path, bytes]] = []
    for path in paths:
        if file_type(str(path)) == "markdown":
            raw, markdown = _source(path)
            frozen_path = path
        else:
            # Unwrapped, and with the display maths blocked out, before anything is
            # hashed: both are habits of pandoc's writer rather than anything the author
            # did, and both are what a field quoting these lines would have to render.
            markdown = _display_maths_blocked(
                _pandoc(str(path), _MARKDOWN, "--wrap=none").decode("utf-8")
            )
            raw = markdown.encode("utf-8")
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
                "so it is not ours to overwrite. Move it aside, or run in2lambda "
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
        # The bytes pandoc wrote, so that the file on disk is what `digest` is of;
        # writing text would rewrite the line endings on Windows and it would not be.
        frozen_path.write_bytes(raw)
    # Freezing is where a draft starts, not something it records: a replay is the log
    # applied to this, so `add` is the only thing that writes a draft it did not run.
    save(
        draft,
        {
            "sources": sources,
            "log": existing["log"],
            "fields": existing["fields"],
            # What the checks found still holds where every file named was frozen
            # already, since then this writes the draft back as it was. A source
            # appended is a document the checks have never seen, every block of which
            # is in no field, so the report is dropped as any change to a draft drops
            # it - and `build`, which is gated on one, asks for the checks again.
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
        where one does, then the line number and the line itself. A draft of more than
        one source heads each with its number and its name, since the line numbers
        start again at 1 in every one of them.

    Raises:
        DraftMissing: there is no draft at that path.
        DraftUnreadable: what is there is not a draft anything here wrote.
        SourceUnreadable: a markdown the draft names has moved, or is not text.
        DraftExists: a markdown has changed since the draft was written from it, so
            the ids would be printed against lines they are not the ids of.
    """
    # A line range is only an address while the lines have not moved: printing ids
    # against markdown the draft was not written from would be worse than printing
    # nothing, because it would look right.
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
