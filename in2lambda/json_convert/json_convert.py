"""Converts questions from a Python set object into Lambda Feedback JSON."""

import json
import os
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from in2lambda.api.response_area import ResponseArea
from in2lambda.api.set import Set

MINIMAL_QUESTION_TEMPLATE = "minimal_template_question.json"
MINIMAL_SET_TEMPLATE = "minimal_template_set.json"
MINIMAL_RESPONSE_AREA_TEMPLATE = "minimal_template_response_area.json"


def _response_area_json(
    response_area: ResponseArea, template: dict[str, Any], order_number: int
) -> dict[str, Any]:
    """Fill a copy of the response-area template from a :class:`ResponseArea`.

    Args:
        response_area: The response area to serialise.
        template: The loaded ``minimal_template_response_area.json``.
        order_number: This response area's position within the part.

    Returns:
        A ``responseAreas`` entry ready for a part's JSON.
    """
    entry = deepcopy(template)
    entry["orderNumber"] = order_number
    entry["evaluationFunctionName"] = response_area.evaluation_function
    entry["gradeParams"] = deepcopy(response_area.grade_params)
    entry["preResponseText"] = response_area.pre_response_text
    entry["postResponseText"] = response_area.post_response_text
    response_input = entry["response"]["responseInput"]
    response_input["responseType"] = response_area.response_type
    response_input["answer"] = response_area.answer
    response_input["config"] = deepcopy(response_area.config)
    return entry


def _apply_part(
    part_json: dict[str, Any], part: Any, response_area_template: dict[str, Any]
) -> None:
    """Copy one :class:`~in2lambda.api.part.Part` into its JSON, response areas included."""
    part_json["content"] = part.text
    part_json["workedSolution"]["content"] = part.worked_solution
    if part.response_areas:
        part_json["responseAreas"] = [
            _response_area_json(response_area, response_area_template, order)
            for order, response_area in enumerate(part.response_areas)
        ]
        # Mirror the first answer into the part's "final answer" field when the
        # filter did not already set one (matches exported questions).
        if not part_json.get("answerContent"):
            part_json["answerContent"] = part.response_areas[0].answer


def _zip_sorted_folder(folder_path, zip_path):
    """Zips the contents of a folder, preserving the directory structure.

    Args:
        folder_path: The path to the folder to zip.
        zip_path: The path where the zip file will be created.
    """
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, dirs, files in os.walk(folder_path):
            # Sort files for deterministic, alphabetical order
            for file in sorted(files):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, folder_path)
                zf.write(abs_path, arcname=rel_path)


def converter(
    question_template: dict[str, Any],
    set_template: dict[str, Any],
    response_area_template: dict[str, Any],
    SetQuestions: Set,
    output_dir: str,
) -> None:
    """Turns a set of question objects into Lambda Feedback JSON.

    Args:
        question_template: The loaded JSON from the minimal question template (it needs to be in sync).
        set_template: The loaded JSON from the minimal set template (it needs to be in sync).
        response_area_template: The loaded JSON from the minimal response-area template.
        SetQuestions: A Set object containing questions.
        output_dir: The absolute path for where to produced the final JSON/zip files.
    """
    ListQuestions = SetQuestions.questions
    set_name = SetQuestions._name
    set_description = SetQuestions._description
    # The name is used both as a path component and as the set file's suffix, so
    # strip anything that isn't filesystem-safe (mirrors the question filenames below).
    set_slug = re.sub(r"[^\w\-_.]", "_", set_name.strip()) or "set"

    # create directory to put the questions
    os.makedirs(output_dir, exist_ok=True)
    output_question = os.path.join(output_dir, set_slug)
    os.makedirs(output_question, exist_ok=True)

    set_template["name"] = set_name
    set_template["description"] = set_description
    set_template["finalAnswerVisibility"] = str(
        SetQuestions._finalAnswerVisibility.status
    )
    set_template["workedSolutionVisibility"] = str(
        SetQuestions._workedSolutionVisibility.status
    )
    set_template["structuredTutorialVisibility"] = str(
        SetQuestions._structuredTutorialVisibility.status
    )
    # create the set file
    with open(f"{output_question}/set_{set_slug}.json", "w") as file:
        json.dump(set_template, file)

    for i in range(len(ListQuestions)):
        output = deepcopy(question_template)

        output["orderNumber"] = i  # order number starts at 0
        # add title to the question file
        if ListQuestions[i].title != "":
            output["title"] = ListQuestions[i].title
        else:
            output["title"] = "Question " + str(i + 1)

        # add main text to the question file
        output["masterContent"] = ListQuestions[i].main_text

        # add parts to the question file
        if ListQuestions[i].parts:
            _apply_part(
                output["parts"][0],
                ListQuestions[i].parts[0],
                response_area_template,
            )
            for j in range(1, len(ListQuestions[i].parts)):
                output["parts"].append(deepcopy(question_template["parts"][0]))
                output["parts"][j]["orderNumber"] = j
                _apply_part(
                    output["parts"][j],
                    ListQuestions[i].parts[j],
                    response_area_template,
                )

        # Output file
        filename = (
            "question_"
            + str(i).zfill(3)
            + "_"
            + re.sub(r"[^\w\-_.]", "_", output["title"].strip())
        )

        # write questions into directory
        with open(f"{output_question}/{filename}.json", "w") as file:
            json.dump(output, file)

        # write image into directory
        for k in range(len(ListQuestions[i].images)):
            image_path = os.path.abspath(
                ListQuestions[i].images[k]
            )  # converts computer path into python path
            # If images exist, create a media directory
            output_image = os.path.join(output_question, "media")
            os.makedirs(output_image, exist_ok=True)
            shutil.copy(image_path, output_image)  # copies image into the directory

    # output zip file in destination folder
    _zip_sorted_folder(output_question, output_question + ".zip")


def main(set_questions: Set, output_dir: str) -> None:
    """Preliminary defensive programming before calling the main converter function.

    This ultimately then produces the Lambda Feedback JSON/ZIP files.

    Args:
        set_questions: A Set object containing questions.
        output_dir: Where to output the final Lambda Feedback JSON/ZIP files.
    """
    # Use path so minimal template can be found regardless of where the user is running python from.
    with open(Path(__file__).with_name(MINIMAL_QUESTION_TEMPLATE), "r") as file:
        question_template = json.load(file)

    with open(Path(__file__).with_name(MINIMAL_SET_TEMPLATE), "r") as file:
        set_template = json.load(file)

    with open(Path(__file__).with_name(MINIMAL_RESPONSE_AREA_TEMPLATE), "r") as file:
        response_area_template = json.load(file)

    # check if directory exists in file
    if os.path.isdir(output_dir):
        try:
            shutil.rmtree(output_dir)
        except OSError as e:
            print("Error: %s : %s" % (output_dir, e.strerror))
    converter(
        question_template,
        set_template,
        response_area_template,
        set_questions,
        output_dir,
    )
