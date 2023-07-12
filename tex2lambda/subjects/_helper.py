"""Various generic helper functions used during the Pandoc filter stage.

They are specifically to handle Math and Image handling.
"""

from functools import cache
from pathlib import Path
from typing import Callable, Optional, Union

import panflute as pf
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


filter_func_type = Callable[
    [Union[pf.Element, pf.Math, pf.Image], pf.elements.Doc, Questions, str],
    Optional[pf.Str],
]


def filter(func: filter_func_type) -> filter_func_type:
    """Python decorator to make generic LaTeX elements Lambda Feedback readable.

    Currently, this involves putting dollar signs around maths expressions and
    using markdown syntax for images.

    Args:
        func: The pandoc filter for a given subject.
    """

    def handle_math_image(
        elem: Union[pf.Element, pf.Math, pf.Image],
        doc: pf.elements.Doc,
        questions: Questions,
        tex_file: str,
    ) -> Optional[pf.Str]:
        """Handles math and image elements within the filter, before calling the original function.

        Args:
            elem: The current TeX element being processed. This could be a paragraph,
                ordered list, etc.
            doc: A Pandoc document container - essentially the Pandoc AST.
            questions: The Python API that is used to store the result after processing
                the TeX file.
            tex_file: The absolute path to the TeX file being parsed.

        Returns:
            Converted TeX elements for the AST where required
        """
        match type(elem):
            case pf.Math:
                expression = latex_to_katex(elem.text)
                return pf.Str(
                    f"${expression}$"
                    if elem.format == "InlineMath"
                    else f"\n\n$$\n{expression}\n\n$$\n\n"
                )

            case pf.Image:
                # TODO: Handle "pdf images" and svg files.
                path = image_path(elem.url, tex_file)
                if path is None:
                    echo(f"Warning: Couldn't find {elem.url}")
                else:
                    questions.add_image(path)
                return pf.Str(f"![pictureTag]({elem.url})")

        return func(elem, doc, questions, tex_file)

    return handle_math_image
