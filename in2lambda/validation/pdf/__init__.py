"""Compiles a set the way Lambda Feedback makes a PDF of it, and reads the errors back.

Lambda Feedback renders question PDFs with lambda-feedback/PDF-generator: pandoc with
``template.latex`` beside this file, then xelatex. Markdown that pipeline refuses is a
fault in the set, so the whole set is compiled once here and each LaTeX error is traced
back to the field it came from.

The trick for tracing is a marker: the document handed to pandoc carries a raw-LaTeX
comment naming the field before each field's markdown, and pandoc copies raw blocks
through untouched. ``xelatex -file-line-error`` then reports every error as
``set.tex:<line>: <message>``, and the last marker above that line names the field. Not
every error, though: a file LaTeX cannot find is announced with no location at all, and
is traced instead through the ``Emergency stop.`` that follows it, which has one.

pandoc and xelatex are both optional, as they are everywhere else in in2lambda: without
them this reports what to install rather than raising.

The same pipeline writes the PDF itself - :func:`render` - since what a reviewer wants
to look at is the document the errors were traced out of.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from in2lambda.api.problem import Problem
from in2lambda.source import SourceError

_TEMPLATE = Path(__file__).with_name("template.latex")
"""The PDF generator's own pandoc template - see the README beside it."""

_TOOLS = {
    "pandoc": "pandoc (see https://pandoc.org/installing.html)",
    "xelatex": (
        "xelatex (apt install texlive-xetex texlive-latex-recommended"
        " texlive-latex-extra texlive-science texlive-lang-chinese"
        " fonts-noto-core fonts-noto-cjk)"
    ),
}

_SET = "The set"
"""Where an error that is not inside any one field is reported against."""

_MARKER = "% in2lambda: "

_ERROR = re.compile(
    r"^(?:\./)?(\S+\.(?:tex|sty|cls|def|cfg|fd|ltx)):(\d+): (.+)$", re.MULTILINE
)
"""One ``-file-line-error`` line. The file is only ``set.tex`` for the set's own text."""

_BARE = re.compile(r"^! (.+)$", re.MULTILINE)
r"""An error xelatex printed with no file and line to it.

``-file-line-error`` only rewrites an error raised at a line of a file. A file that
cannot be found is announced through ``\typeout`` rather than raised, and an error
raised once the input has run out - ``File ended while scanning use of \frac`` - has no
line left to name, so both are only ever in the log behind a ``!``.
"""

_STOP = "Emergency stop."
"""TeX's last line, which says where it gave up rather than what was wrong."""

_IMAGE = re.compile(r"(!\[[^\]]*\]\()([^)]*)(\))")
"""A markdown image with its path apart, so that the path can be rewritten or dropped."""

_TIMEOUT = 120
"""Seconds for pandoc or xelatex. A set that takes longer is reported, not waited for."""


class CompileFailed(SourceError):
    """The pipeline produced nothing at all.

    Either pandoc refused the set, or xelatex wrote no PDF, or neither finished. Not a
    problem in one field, since there is no generated LaTeX to trace an error back
    through, so it is raised rather than reported - as a `SourceError`, which is what
    the command line turns into a message rather than a traceback.
    """


def missing_tools() -> list[str]:
    """What is needed to compile a set but is not installed, each saying how to get it.

    Returns:
        One line per missing tool, or an empty list if a set can be compiled here.
    """
    return [hint for tool, hint in _TOOLS.items() if shutil.which(tool) is None]


def problems(fields: list[tuple[str, str]], images: list[str]) -> list[Problem]:
    """Everything the PDF generator's pandoc and xelatex refuse, by the field it is in.

    Args:
        fields: Every markdown field of the set in the order it is written, each with
            the location - ``Question 1 "Title", part (a), text`` - to report against.
        images: Every image path the set's questions hold. Those that exist are put
            beside the compiled document under their file name, since that is how the
            export refers to them; a reference to any other is dropped, as the image
            check already reports it.

    Returns:
        One :class:`~in2lambda.api.problem.Problem` per distinct LaTeX error. An empty
        list means the set compiles as Lambda Feedback will compile it.
    """
    if missing := missing_tools():
        return [
            Problem(
                _SET,
                "not compiled as the PDF generator would: install "
                + " and ".join(missing),
            )
        ]

    try:
        return _compiled(fields, images)
    except CompileFailed as failed:
        return [Problem(_SET, str(failed))]


def render(
    fields: list[tuple[str, str]], images: list[str], output: Path
) -> list[Problem]:
    """Writes the PDF Lambda Feedback's generator would make of these fields.

    Args:
        fields: Every markdown field to render, each with the location to report an
            error in it against, as :func:`problems` takes them.
        images: Every image path the fields refer to, as :func:`problems` takes them.
        output: The PDF file to write. Its directory is made if it is not there, and a
            file of that name is overwritten.

    Returns:
        One :class:`~in2lambda.api.problem.Problem` per LaTeX error, as
        :func:`problems` reports them. xelatex typesets what it can whatever it
        refuses, so these say what to look at in the PDF rather than that there is none.

    Raises:
        CompileFailed: pandoc refused the fields, neither tool finished, or xelatex
            wrote no PDF at all.
    """
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        latex, log = _compile(fields, images, work)
        problems = _reported(log, _locations(latex))
        if not (compiled := work / "set.pdf").is_file():
            # Why nothing was typeset and not merely that nothing was: whatever stopped
            # xelatex is among the problems like any other error, traced to the field
            # the stop happened in where there is one.
            said = "; ".join(str(problem) for problem in problems)
            raise CompileFailed(
                f"xelatex produced no PDF of {output.name}"
                + (f": {said}" if said else ".")
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(compiled, output)
        return problems


def _compiled(fields: list[tuple[str, str]], images: list[str]) -> list[Problem]:
    """The set's errors, compiled in a directory of its own and thrown away again."""
    with tempfile.TemporaryDirectory() as directory:
        latex, log = _compile(fields, images, Path(directory))
        return _reported(log, _locations(latex))


def _compile(
    fields: list[tuple[str, str]], images: list[str], work: Path
) -> tuple[str, str]:
    """The set run through pandoc and then xelatex in `work`.

    Returns:
        The LaTeX pandoc generated, whose markers say which field each line came from,
        and the xelatex log. Whatever xelatex managed to typeset is left in `work` as
        ``set.pdf``.

    Raises:
        CompileFailed: pandoc would not read the set, so there is no LaTeX to run, or
            one of the two did not finish. A set can be written that makes TeX loop
            forever, which is a fault in the set like any other: both callers want it
            said rather than waited for, so it is said here once.
    """
    try:
        return _run(fields, images, work)
    except subprocess.TimeoutExpired as expired:
        raise CompileFailed(
            f"the PDF generator cannot compile this: {expired.cmd[0]} did not"
            f" finish within {_TIMEOUT} seconds"
        ) from None


def _run(
    fields: list[tuple[str, str]], images: list[str], work: Path
) -> tuple[str, str]:
    """The two commands themselves, whatever either of them does."""
    available = set()
    for image in images:
        if Path(image).is_file():
            shutil.copy(image, work / Path(image).name)
            available.add(Path(image).name)

    run = subprocess.run(
        [
            "pandoc",
            "-f",
            "markdown-implicit_figures",
            "-t",
            "latex",
            "-s",
            f"--template={_TEMPLATE}",
            "-o",
            "set.tex",
        ],
        input=_marked_document(fields, available),
        capture_output=True,
        text=True,
        # Not the locale's encoding: a set holding any non-ASCII character would
        # then fail to even be handed over under, say, LC_ALL=C.
        encoding="utf-8",
        cwd=work,
        timeout=_TIMEOUT,
    )
    if run.returncode:
        raise CompileFailed(f"pandoc cannot read the set: {run.stderr.strip()}")

    latex = (work / "set.tex").read_text(encoding="utf-8")
    run = subprocess.run(
        [
            "xelatex",
            "-interaction=nonstopmode",
            "-file-line-error",
            "-no-shell-escape",
            "set.tex",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=work,
        timeout=_TIMEOUT,
    )
    return latex, run.stdout


def _marked_document(fields: list[tuple[str, str]], available: set[str]) -> str:
    """The whole set as one markdown document, each field under a marker naming it.

    The fence is four backticks so that a field which itself contains a code block
    cannot close the marker's raw-LaTeX block early.
    """
    blocks = []
    for location, markdown in fields:
        markdown = _IMAGE.sub(
            lambda image: (
                f"{image[1]}{Path(image[2]).name}{image[3]}"
                if Path(image[2]).name in available
                else ""
            ),
            markdown,
        )
        blocks.append(f"````{{=latex}}\n{_MARKER}{location}\n````\n\n{markdown}\n")
    return "\n".join(blocks)


def _locations(latex: str) -> list[tuple[int, str]]:
    """Each marker in the generated LaTeX as the line it is on and the field it names."""
    return [
        (number, line.partition(_MARKER)[2])
        for number, line in enumerate(latex.splitlines(), start=1)
        if line.startswith(_MARKER)
    ]


def _where(file: str, line: int, locations: list[tuple[int, str]]) -> str:
    """The field this line of this file is in, or `_SET` if it is in none of them.

    Only ``set.tex`` holds the set's own text, so a line of a package or a font is
    nothing to do with the markers however it numbers.
    """
    where = _SET
    if file == "set.tex":
        for number, location in locations:
            if number <= line:
                where = location
    return where


def _reported(log: str, locations: list[tuple[int, str]]) -> list[Problem]:
    """The xelatex log's errors as problems, each against the field it happened in.

    The same error repeated - a command used twice, say - is one problem, since the
    author has one thing to go and fix. An error printed bare is reported where the
    ``Emergency stop.`` after it says the reading had got to, that being the only line
    of an abort with a location on it, and the stop itself only when there is nothing
    else to say.
    """
    bare = [message.strip() for message in _BARE.findall(log)]
    stop = _SET if _STOP in bare else None

    errors = []
    for error in _ERROR.finditer(log):
        file, line, message = error[1], int(error[2]), error[3].strip()
        if message == _STOP:
            stop = _where(file, line, locations)
        else:
            errors.append((_where(file, line, locations), message))

    # Only the first bare error: whatever follows it is TeX unwinding from it, and the
    # author has the one thing to go and fix.
    if causes := [message for message in bare if message != _STOP]:
        errors.append((stop or _SET, causes[0]))
    elif not errors and stop:
        errors.append((stop, _STOP))

    found: list[Problem] = []
    for where, message in errors:
        problem = Problem(where, f"the PDF generator cannot compile this: {message}")
        if problem not in found:
            found.append(problem)
    return found
