"""Compiles a set the way Lambda Feedback makes a PDF of it, and reads the errors back.

Lambda Feedback renders question PDFs with lambda-feedback/PDF-generator: pandoc with
``template.latex`` beside this file, then xelatex. Markdown that pipeline refuses is a
fault in the set, so the whole set is compiled once here and each LaTeX error is traced
back to the field it came from.

The trick for tracing is a marker: the document handed to pandoc carries a raw-LaTeX
comment naming the field before each field's markdown, and pandoc copies raw blocks
through untouched. ``xelatex -file-line-error`` then reports every error as
``set.tex:<line>: <message>``, and the last marker above that line names the field.

pandoc and xelatex are both optional, as they are everywhere else in in2lambda: without
them this reports what to install rather than raising.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from in2lambda.api.problem import Problem

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

_IMAGE = re.compile(r"(!\[[^\]]*\]\()([^)]*)(\))")
"""A markdown image with its path apart, so that the path can be rewritten or dropped."""

_TIMEOUT = 120
"""Seconds for pandoc or xelatex. A set that takes longer is reported, not waited for."""


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
    except subprocess.TimeoutExpired as expired:
        # TeX can be made to loop forever, which is itself a fault in the set.
        return [
            Problem(
                _SET,
                f"the PDF generator cannot compile this: {expired.cmd[0]} did not"
                f" finish within {_TIMEOUT} seconds",
            )
        ]


def _compiled(fields: list[tuple[str, str]], images: list[str]) -> list[Problem]:
    """The set run through pandoc and then xelatex in a directory of its own."""
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
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
            return [Problem(_SET, f"pandoc cannot read the set: {run.stderr.strip()}")]

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
        return _reported(run.stdout, _locations(latex))


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


def _reported(log: str, locations: list[tuple[int, str]]) -> list[Problem]:
    """The xelatex log's errors as problems, each against the field it happened in.

    The same error repeated - a command used twice, say - is one problem, since the
    author has one thing to go and fix.
    """
    found = []
    for error in _ERROR.finditer(log):
        file, line, message = error[1], int(error[2]), error[3].strip()
        where = _SET
        if file == "set.tex":
            for number, location in locations:
                if number <= line:
                    where = location
        problem = Problem(where, f"the PDF generator cannot compile this: {message}")
        if problem not in found:
            found.append(problem)
    return found
