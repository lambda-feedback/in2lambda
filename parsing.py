import json
import pprint
from pathlib import Path
from typing import Any, Literal, Optional, Tuple, TypedDict, cast

import pypandoc

from katex_convert import latex_to_katex

FILENAME = "./problemsA_v2.7.tex"
"""Path to the TeX file to parse."""

ORDERED_LIST_PART_INDEX = 1
"""Index of the list of parts within ordered list content."""


class Part(TypedDict):
    """A part of a question as represented on Lambda Feedback."""

    Text: str
    Answer: str


class Question(TypedDict):
    """A full question as represented on Lambda Feedback."""

    Title: str
    MainText: str
    Parts: list[Part]


class MainBlock(TypedDict):
    """The overarching top-level block type as produced by Pandoc."""

    t: Literal["Header", "Para", "OrderedList", "Div"]
    c: Any


class ParaBlock(TypedDict):
    """A paragraph block as produced by Pandoc."""

    t: Literal["Str", "Space", "Math"]
    c: Any


class MathTypes(TypedDict):
    """The possible types of maths equations."""

    t: Literal["DisplayMath", "InlineMath"]


MathExpression = str


class MathBlock(TypedDict):
    """A maths block as produced by Pandoc."""

    t: Literal["Math"]
    c: Tuple[MathTypes, MathExpression]


class File:
    """Represents a TeX file as passed in by a user."""

    def __init__(self, filename: str):
        """Detemines the image directories referenced by the file and it's Pandoc JSON format.

        Args:
            filename: The path to the TeX file.
        """
        self.filename = filename
        """The path to the TeX file."""

        self.image_directories = self.__image_directories()
        """A list of image directories referenced by the file as denoted by `graphicspath`."""

        self.json: list[MainBlock] = json.loads(
            pypandoc.convert_file(self.filename, "json")
        )["blocks"]
        """The Pandoc-parsed version of the file."""

    def __image_directories(self) -> Optional[list[str]]:
        """Private function to determine the directories of images referenced in `graphicspath`.

        Returns:
            A list of directories referenced by `graphicspath`, or None if there aren't any.
        """
        with open(self.filename, "r") as file:
            for line in file:
                # Assumes line is in the format \graphicspath{ {...}, {...}, ...}
                if "graphicspath" in line:
                    return [
                        i.strip("{").rstrip("}")
                        for i in line.replace(" ", "")[
                            len("\graphicspath{") : -1
                        ].split(",")
                    ]
        return None

    def image_path(self, image_name: str) -> Optional[str]:
        """Determines the path to an image referenced in the given file.

        Note that this is either relative or absolute depending on what's set in
        ``graphicspath`

        Args:
            image_name: The file name of the image e.g. example.png

        Returns:
            The path to the image if it exists within `graphicspath`. If not, it returns None.
        """
        if self.image_directories is None:
            return None
        for directory in self.image_directories:
            if directory[-1] != "/":
                directory += "/"
            filename = directory + image_name
            if Path(filename).is_file():
                return filename
        return None

    def __repr__(self) -> str:
        """A human-readable expression for a File object."""
        return f"File({self.filename})"


def determine_question_part(
    currentBlock: MainBlock, precedingBlock: MainBlock
) -> Literal["Main", "Part", "Solution", "Other"]:
    """Determines whether a Pandoc block denotes a section as specified by Lambda FeedBack.

    Args:
        currentBlock: A top-level Pandoc block.
        precedingBlock: The top-level Pandoc block before the current block.

    Returns:
        A string denoting what Lambda Feedback section the block is part of.

        Main: The text body of the question.
        Part: An individual question part.
        Solution: The solution to the question.
        Other: An unknown or not relevant section.
    """
    if precedingBlock["t"] == "Header" and currentBlock["t"] == "Para":
        return "Main"
    if precedingBlock["t"] == "Para" and currentBlock["t"] == "OrderedList":
        return "Part"
    if currentBlock["t"] == "Div" and currentBlock["c"][0][1][0] == "solution":
        return "Solution"
    return "Other"


def extract_para_text(contents: list[ParaBlock]) -> str:
    """Parses a list of Pandoc paragraph content.

    Make sure to remove the `para` t type beforehand, this only handles the contents list.

    Args:
        contents: A list of Pandoc paragraph contents, excluding the `para` type.

    Returns:
        A string representing the LaTeX's paragraph contents.
    """
    result = ""
    for item in contents:
        match item["t"]:
            case "Str":
                result += item["c"]
            case "Space":
                result += " "
            case "Math":
                cast(MathBlock, item)
                expression = latex_to_katex(item["c"][1])
                result += (
                    "$" + expression + "$"
                    if item["c"][0]["t"] == "InlineMath"
                    else "\n\n$$\n" + expression + "\n\n$$\n\n"
                )
    return result


def extract_parts(parts: list[list[ParaBlock]]) -> list[Part]:
    """Extracts the parts from a list of Pandoc paragraph blocks.

    Args:
        parts: A list of parts denoted by paragraph blocks, where each part is in its own singleton list.

    Returns:
        A list of parts with an empty solution.
    """
    result = []
    for part in parts:
        result.append(Part(Text=extract_para_text(part[0]["c"]), Answer=""))
    return result


def extract_answer(answer_parts: list[MainBlock]) -> str:
    """Takes a list of top-level Pandoc blocks and returns the contents of any paragraph blocks.

    Args:
        answer_parts: A list ot top-level Pandoc blocks that denotes an answer.
            For example, it could be a list of paragraph blocks.

    Returns:
        A string representing the LaTeX answer contents.
    """
    result = ""
    for answer_part in answer_parts:
        if answer_part["t"] == "Para":
            result += extract_para_text(answer_part["c"]) + "\n\n"
    return result


if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)

    questions: list[Question] = []
    file = File(FILENAME)

    for blockId, block in enumerate(file.json):
        if blockId != 0:
            match determine_question_part(block, file.json[blockId - 1]):
                case "Main":
                    # Add the main question text as a part
                    questions.append(
                        Question(
                            Title="",
                            MainText="",
                            Parts=[Part(Text=extract_para_text(block["c"]), Answer="")],
                        )
                    )
                case "Part":
                    # Undo the "Main" case: Set the main question text to what's currently the part (a) text
                    # Then set the parts based on the list
                    questions[-1]["MainText"] = questions[-1]["Parts"][0]["Text"]
                    questions[-1]["Parts"] = extract_parts(
                        block["c"][ORDERED_LIST_PART_INDEX]
                    )
                case "Solution":
                    result = extract_answer(block["c"][1][1:])
                    for part in questions[-1]["Parts"]:
                        part["Answer"] = result

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(questions)
