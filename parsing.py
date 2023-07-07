import json
import pprint
from pathlib import Path
from typing import Any, Literal, Optional, Tuple, TypedDict, cast

import pypandoc

from katex_convert import latex_to_katex

FILENAME = "problemsA_v2.7.tex"

ORDERED_LIST_PART_INDEX = 1
"""Index of the list of parts within ordered list content."""


class Part(TypedDict):
    Text: str
    Answer: str


class Question(TypedDict):
    Title: str
    MainText: str
    Parts: list[Part]


class MainBlock(TypedDict):
    t: Literal["Header", "Para", "OrderedList", "Div"]
    c: Any


class ParaBlock(TypedDict):
    t: Literal["Str", "Space", "Math"]
    c: Any


class MathTypes(TypedDict):
    t: Literal["DisplayMath", "InlineMath"]


MathExpression = str


class MathBlock(TypedDict):
    t: Literal["Math"]
    c: Tuple[MathTypes, MathExpression]


class File:
    def __init__(self, filename: str):
        self.filename = filename
        self.image_directories = self.__image_directories()
        self.json: list[MainBlock] = json.loads(
            pypandoc.convert_file(self.filename, "json")
        )["blocks"]

    def __image_directories(self) -> Optional[list[str]]:
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
        return f"File({self.filename})"


def determine_question_part(
    precedingBlock: MainBlock, currentBlock: MainBlock
) -> Literal["Main", "Part", "Solution", "Other"]:
    if precedingBlock["t"] == "Header" and currentBlock["t"] == "Para":
        return "Main"
    if precedingBlock["t"] == "Para" and currentBlock["t"] == "OrderedList":
        return "Part"
    if currentBlock["t"] == "Div" and currentBlock["c"][0][1][0] == "solution":
        return "Solution"
    return "Other"


# Takes in the contents part (remove the t type beforehand)
def extract_para_text(contents: list[ParaBlock]) -> str:
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
                    else "$$" + expression + "$$"
                )
    return result


# A list of parts, where each part is in its own singleton list
# Returns a list of parts with an empty solution
def extract_parts(parts: list[list[ParaBlock]]) -> list[Part]:
    result = []
    for part in parts:
        result.append(Part(Text=extract_para_text(part[0]["c"]), Answer=""))
    return result


def extract_answer(answer_parts: list[MainBlock]) -> str:
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
            match determine_question_part(file.json[blockId - 1], block):
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
