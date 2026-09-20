"""Compiles a set as Lambda Feedback makes a PDF of it, and reads the errors back.

Lambda Feedback renders question PDFs with lambda-feedback/PDF-generator: pandoc with
``template.latex`` beside this file, then xelatex. Markdown that pipeline refuses is a
fault in the set, so this module compiles the whole set once and traces each LaTeX error
back to the field it came from.

A marker does the tracing. The document handed to pandoc holds a raw-LaTeX comment naming
each field before that field's markdown, and pandoc copies raw blocks through unchanged.
``xelatex -file-line-error`` reports every error as ``set.tex:<line>: <message>``, and the
last marker above that line names the field. Some errors carry no location: xelatex
announces a file it cannot find without one, and this module traces that error through the
``Emergency stop.`` after it, which carries a location.

pandoc and xelatex are both optional, as they are everywhere else in in2lambda. Without
them this module names the packages to install and raises nothing.

The same pipeline writes the PDF itself - :func:`render` - because a reviewer reads the
document the errors were traced out of.
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
"""Each tool a compile needs, by the name on the PATH, with how to install it."""

_SET = "The set"
"""The location reported for an error that falls in no one field."""

_MARKER = "% in2lambda: "

_ERROR = re.compile(
    r"^(?:\./)?(\S+\.(?:tex|sty|cls|def|cfg|fd|ltx)):(\d+): (.+)$", re.MULTILINE
)
"""One ``-file-line-error`` line. Only ``set.tex`` holds the set's own text."""

_BARE = re.compile(r"^! (.+)$", re.MULTILINE)
r"""An error xelatex printed with no file and no line.

``-file-line-error`` rewrites only an error raised at a line of a file. xelatex announces
a file it cannot find through ``\typeout`` and does not raise it, and an error raised once
the input has run out - ``File ended while scanning use of \frac`` - has no line left to
name, so the log holds both behind a ``!``.
"""

_STOP = "Emergency stop."
"""TeX's last line, which names where it gave up and not what was wrong."""

_IMAGE = re.compile(r"(!\[[^\]]*\]\()([^)]*)(\))")
"""A markdown image with its path apart, so that the path can be rewritten or dropped."""

_TIMEOUT = 120
"""Seconds for pandoc or xelatex. A set taking longer is reported, and not awaited."""


class CompileFailed(SourceError):
    """The pipeline produced no PDF.

    pandoc refused the set, or xelatex wrote no PDF, or one of the two did not finish.
    No generated LaTeX is left to trace an error through, so this is raised and not
    reported as a problem in one field. `CompileFailed` subclasses `SourceError`, which
    the command line prints as a message and not as a traceback.
    """


def missing_tools() -> list[str]:
    """The tools a compile needs that are not installed, each with how to install it.

    Returns:
        One line per missing tool, or an empty list where a set can be compiled here.
    """
    return [hint for tool, hint in _TOOLS.items() if shutil.which(tool) is None]


def problems(fields: list[tuple[str, str]], images: list[str]) -> list[Problem]:
    """Everything the PDF generator's pandoc and xelatex refuse, by the field it is in.

    Args:
        fields: Every markdown field of the set in the order it is written, each with
            the location - ``Question 1 "Title", part (a), text`` - to report against.
        images: Every image path the set's questions hold. An image that exists is copied
            beside the compiled document under its file name, which is how the export
            refers to it. A reference to any other image is dropped, because
            `in2lambda.validation` already reports it.

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
        output: The PDF file to write. Its directory is created where it does not exist,
            and a file of that name is overwritten.

    Returns:
        One :class:`~in2lambda.api.problem.Problem` per LaTeX error, as :func:`problems`
        reports them. xelatex typesets what it can whatever it refuses, so each problem
        names what to read in the PDF.

    Raises:
        CompileFailed: pandoc refused the fields, neither tool finished, or xelatex
            wrote no PDF at all.
    """
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        latex, log = _compile(fields, images, work)
        problems = _reported(log, _locations(latex))
        if not (compiled := work / "set.pdf").is_file():
            # The message names why xelatex typeset nothing: whatever stopped it is among
            # the problems like any other error, traced to the field the stop happened
            # in where a field holds it.
            said = "; ".join(str(problem) for problem in problems)
            raise CompileFailed(
                f"xelatex produced no PDF of {output.name}"
                + (f": {said}" if said else ".")
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(compiled, output)
        return problems


def _compiled(fields: list[tuple[str, str]], images: list[str]) -> list[Problem]:
    """The set's errors, compiled in a directory of its own and deleted again."""
    with tempfile.TemporaryDirectory() as directory:
        latex, log = _compile(fields, images, Path(directory))
        return _reported(log, _locations(latex))


def _compile(
    fields: list[tuple[str, str]], images: list[str], work: Path
) -> tuple[str, str]:
    """The set run through pandoc and then xelatex in `work`.

    Returns:
        The LaTeX pandoc generated, whose markers name the field each line came from, and
        the xelatex log. Whatever xelatex typeset is left in `work` as ``set.pdf``.

    Raises:
        CompileFailed: pandoc would not read the set, so there is no LaTeX to run, or one
            of the two commands did not finish. A set can be written that makes TeX loop
            forever, which is a fault in the set like any other, and neither caller waits
            for it, so this function reports it once.
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
    """The two commands themselves, whatever either of them returns."""
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
        # Not the locale's encoding: under LC_ALL=C a set holding any character outside
        # ASCII would fail before pandoc read it.
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

    The fence is four backticks, so that a field holding a code block does not close the
    marker's raw-LaTeX block early.
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
    """Each marker in the generated LaTeX, as the line it is on and the field it names."""
    return [
        (number, line.partition(_MARKER)[2])
        for number, line in enumerate(latex.splitlines(), start=1)
        if line.startswith(_MARKER)
    ]


def _where(file: str, line: int, locations: list[tuple[int, str]]) -> str:
    """The field this line of this file falls in, or `_SET` where it falls in none.

    Only ``set.tex`` holds the set's own text, so a line of a package or a font matches
    no marker whatever its number.
    """
    where = _SET
    if file == "set.tex":
        for number, location in locations:
            if number <= line:
                where = location
    return where


def _reported(log: str, locations: list[tuple[int, str]]) -> list[Problem]:
    """The xelatex log's errors as problems, each against the field it happened in.

    The same error repeated - a command used twice - is one problem, because the author
    has one thing to fix. An error printed bare is reported where the ``Emergency stop.``
    after it says the reading reached, that being the only line of an abort carrying a
    location. The stop itself is reported where there is nothing else to report.
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
    # author has one thing to fix.
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
