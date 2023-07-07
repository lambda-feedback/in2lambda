import json
import pprint
from typing import Any, Literal, Tuple, TypedDict, cast

import pypandoc
from katex_convert import latex_to_katex

FILENAME = "problemsA_v2.7.tex"

ORDERED_LIST_PART_INDEX = 1
"""Index of the list of parts within ordered list content."""


class Part(TypedDict):
    Text: str
    Answer: str


class Question(TypedDict):
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


def generate_json(filename: str) -> list[MainBlock]:
    """Produces Pandoc AST/JSON based on a LaTeX file."""
    # Retrieves only the blocks, and casts it to a list of blocks
    return cast(
        list[MainBlock], json.loads(pypandoc.convert_file(filename, "json"))["blocks"]
    )


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
    parsed_data = generate_json(FILENAME)
    for blockId, block in enumerate(parsed_data):
        if blockId != 0:
            match determine_question_part(parsed_data[blockId - 1], block):
                case "Main":
                    # Add the main question text as a part
                    questions.append(
                        Question(
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
