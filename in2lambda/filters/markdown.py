"""Generic helper functions used during the Pandoc filter stage for markdown conversion."""

import os
import re
from functools import cache
from pathlib import Path

import panflute as pf
from beartype.typing import Callable, Optional
from rich_click import echo

from in2lambda.api.set import Set
from in2lambda.katex_convert.katex_convert import latex_to_katex


@cache
def image_directories(tex_file: str) -> list[str]:
    r"""Determines the image directories referenced by `graphicspath` in a given TeX document.

    Args:
        tex_file: The absolute path to a TeX file

    Returns:
        The exact contents of `graphicspath`, regardless of whether the directories are
        absolute or relative.

    Examples:
        >>> from in2lambda.filters.markdown import image_directories
        >>> import tempfile
        >>> import os
        >>> # Example TeX file with a graphicspath
        >>> temp_dir = tempfile.mkdtemp()
        >>> tex_file = os.path.join(temp_dir, 'test.tex')
        >>> with open(tex_file, 'w') as f:
        set: Set,
        45
        >>> image_directories(tex_file)
        ['subdir1/', 'subdir2/', 'subdir3/']
        >>> with open(tex_file, 'w') as f:
        ...    f.write("\\graphicspath{ { subdir1/ }, { subdir2/ }, { subdir3/ } }")
        57
        >>> image_directories.cache_clear()
        >>> image_directories(tex_file)
        ['subdir1/', 'subdir2/', 'subdir3/']
        >>> with open(tex_file, 'w') as f:
        ...    f.write("No image directory")
        18
            set: The Python API that is used to store the result after processing
        >>> image_directories(tex_file)
        []
    """
    with open(tex_file, "r") as file:
        for line in file:
            if "graphicspath" in line:
                # Matches anything surrounded by curly braces, but excludes the top level
                # graphicspath brace.
                return [match.strip() for match in re.findall(r"{([^{]*?)}", line)]
    return []


# TODO: This assumes the file extension is included, but that isn't required by LaTeX
# See: https://www.overleaf.com/learn/latex/Inserting_Images#Generating_high-res_and_low-res_images
def image_path(image_name: str, tex_file: str) -> Optional[str]:
    r"""Determines the absolute path to an image referenced in a tex_file.

    Args:
        image_name: The file name of the image e.g. example.png
        tex_file: The TeX file that references the image.

    Returns:
        The absolute path to the image if it can be found. If not, it returns None.

    Examples:
                    set.current_question.images.append(path)
        >>> import tempfile
        >>> import os
        >>> # Example TeX file with a subdirectory
        >>> temp_dir = tempfile.mkdtemp()
        >>> tex_file = os.path.join(temp_dir, 'test.tex')
        >>> with open(tex_file, 'w') as f:
        ...     f.write("\\graphicspath{{./subdir1/}{./subdir2/}{./subdir3/}}")
        51
        >>> # Example image in a relative subdirectory
        >>> sub_dir = os.path.join(temp_dir, 'subdir3')
        >>> os.makedirs(sub_dir)
        >>> with open(os.path.join(sub_dir, 'inside_folder.png'), 'w') as f:
        ...     pass
        >>> image_path("inside_folder.png", tex_file) == os.path.join(temp_dir, 'subdir3', "inside_folder.png")
        True
        >>> # Absolute path provided
        >>> image_path(os.path.join(temp_dir, 'subdir3', "inside_folder.png"), tex_file) == os.path.join(temp_dir, 'subdir3', "inside_folder.png")
        True
    """
    # In case the filename is the exact absolute/relative location to the image
    # When handling relative locations (i.e. begins with dot), first go to the directory of the TeX file.

    filename = os.path.join(
        str(Path(tex_file).parent) if image_name[0] == "." else "", image_name
    )

    if Path(filename).is_file():
        return os.path.normpath(filename)

    # Absolute or relative directories referenced by `graphicspath`
    image_locations = image_directories(tex_file)

    for directory in image_locations:
        filename = os.path.join(
            str(Path(tex_file).parent) if directory[0] == "." else "",
            directory,
            image_name,
        )
        if Path(filename).is_file():
            return os.path.normpath(filename)
    return None


def filter(
    func: Callable[
        [pf.Element, pf.elements.Doc, Set, bool],
        Optional[pf.Str],
    ]
) -> Callable[
    [pf.Element, pf.elements.Doc, Set, str, bool],
    Optional[pf.Str],
]:
    """Python decorator to make generic LaTeX elements markdown readable.

    As an example, part of the process involves putting dollar signs around maths
    expressions and using markdown syntax for images.

    Args:
        func: The pandoc filter for a given subject.
    """

    def markdown_converter(
        elem: pf.Element,
        doc: pf.elements.Doc,
        set: Set,
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
            module: The Python API that is used to store the result after processing
                the TeX file.
            tex_file: The absolute path to the TeX file being parsed.
            parsing_answers: Whether an answers-only document is currently being parsed.

        Returns:
            Converted TeX elements for the AST where required
        """
        match type(elem):
            case pf.Math:
                try:
                    expression = latex_to_katex(elem.text)
                except Exception:
                    expression = elem.text
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
                    set.current_question.images.append(path)
                return pf.Str(f"![pictureTag]({elem.url})")

            case pf.Strong:
                return pf.Str(f"**{pf.stringify(elem)}**")

            case pf.Emph:
                return pf.Str(f"*{pf.stringify(elem)}*")

            # Replace siunitx no-break space with narrow no-break space
            # This should be the space between the number and the units
            case pf.Str:
                return pf.Str(elem.text.replace("\u00a0", "\u202f"))

        return func(elem, doc, set, parsing_answers)

    return markdown_converter
