"""Generic helper functions used during the Pandoc filter stage for markdown conversion."""

from functools import cache
from pathlib import Path

import panflute as pf
from beartype.typing import Callable, Optional
from rich_click import echo

from tex2lambda.katex_convert.katex_convert import latex_to_katex
from tex2lambda.question import Questions


@cache
def image_directories(tex_file: str) -> list[str]:
    """Determines the image directories referenced by `graphicspath` in a given TeX document.

    Args:
        tex_file: The absolute path to a TeX file

    Returns:
        The exact contents of `graphicspath`, regardless of whether the directories are
        absolute or relative.
    """
    with open(tex_file, "r") as file:
        for line in file:
            # Assumes line is in the format \graphicspath{ {...}, {...}, ...}
            if "graphicspath" in line:
                return [
                    i.strip("{").rstrip("}")
                    for i in line.replace(" ", "")[len("\graphicspath{") : -1].split(
                        ","
                    )
                ]
    return []


def image_path(image_name: str, tex_file: str) -> Optional[str]:
    """Determines the absolute path to an image referenced in a tex_file.

    Args:
        image_name: The file name of the image e.g. example.png
        tex_file: The TeX file that references the image.

    Returns:
        The absolute path to the image if it can be found. If not, it returns None.
    """
    # In case the filename is the exact absolute/relative location to the image
    # When handling relative locations (i.e. begins with dot), first go to the directory of the TeX file.
    filename = (
        f"{str(Path(tex_file).parent)}/" if image_name[0] == "." else ""
    ) + image_name

    if Path(filename).is_file():
        return filename

    # Absolute or relative directories referenced by `graphicspath`
    image_locations = image_directories(tex_file)

    for directory in image_locations:
        if directory[-1] != "/":
            directory += "/"
        filename = (
            (f"{str(Path(tex_file).parent)}/" if directory[0] == "." else "")
            + directory
            + image_name
        )
        if Path(filename).is_file():
            return filename
    return None


def filter(
    func: Callable[
        [pf.Element, pf.elements.Doc, Questions, bool],
        Optional[pf.Str],
    ]
) -> Callable[[pf.Element, pf.elements.Doc, Questions, str, bool], Optional[pf.Str],]:
    """Python decorator to make generic LaTeX elements markdown readable.

    As an example, part of the process involves putting dollar signs around maths
    expressions and using markdown syntax for images.

    Args:
        func: The pandoc filter for a given subject.
    """

    def markdown_converter(
        elem: pf.Element,
        doc: pf.elements.Doc,
        questions: Questions,
        tex_file: str,
        parsing_answers: bool,
    ) -> Optional[pf.Str]:
        """Handles LaTeX elements within the filter, before calling the original function.

        N.B. tex_file is required to determine where the relative image directory is.
        The argument is not passed to functions that utilise the decorator.

        Args:
            elem: The current TeX element being processed. This could be a paragraph,
                ordered list, etc.
            doc: A Pandoc document container - essentially the Pandoc AST.
            questions: The Python API that is used to store the result after processing
                the TeX file.
            tex_file: The absolute path to the TeX file being parsed.
            parsing_answers: Whether an answers-only document is currently being parsed.

        Returns:
            Converted TeX elements for the AST where required
        """
        match type(elem):
            case pf.Math:
                expression = latex_to_katex(elem.text)
                return pf.Str(
                    f"${expression}$"
                    if elem.format == "InlineMath"
                    else f"\n\n$$\n{expression}\n$$\n\n"
                )

            case pf.Image:
                # TODO: Handle "pdf images" and svg files.
                path = image_path(elem.url, tex_file)
                if path is None:
                    echo(f"Warning: Couldn't find {elem.url}")
                else:
                    questions.add_image(path)
                return pf.Str(f"![pictureTag]({elem.url})")

            case pf.Strong:
                return pf.Str(f"**{pf.stringify(elem)}**")

            case pf.Emph:
                return pf.Str(f"*{pf.stringify(elem)}*")

            # Replace siunitx no-break space with narrow no-break space
            # This should be the space between the number and the units
            case pf.Str:
                return pf.Str(elem.text.replace("\u00a0", "\u202f"))

        return func(elem, doc, questions, parsing_answers)

    return markdown_converter
