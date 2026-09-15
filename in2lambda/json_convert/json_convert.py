"""Converts questions between a Python set object and Lambda Feedback JSON."""

import json
import os
import re
import shutil
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.set import Set
from in2lambda.api.visibility_status import VisibilityController, VisibilityStatus

MINIMAL_QUESTION_TEMPLATE = "minimal_template_question.json"
MINIMAL_SET_TEMPLATE = "minimal_template_set.json"


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


def _question_json(
    question: Question, i: int, template: dict[str, Any]
) -> dict[str, Any]:
    output = deepcopy(template)

    output["orderNumber"] = i  # order number starts at 0
    output["title"] = question.title if question.title != "" else f"Question {i + 1}"
    output["masterContent"] = question.main_text

    output["publish"] = question.publish
    output["displayFinalAnswer"] = question.display_final_answer
    output["displayWorkedSolution"] = question.display_worked_solution
    output["displayStructuredTutorial"] = question.display_structured_tutorial
    output["displayChatbot"] = question.display_chatbot
    # Unset optional settings are omitted rather than given a value Lambda Feedback
    # never chose.
    for key, value in {
        "skill": question.skill,
        "guidance": question.guidance,
        "durationLowerBound": question.duration_lower_bound,
        "durationUpperBound": question.duration_upper_bound,
    }.items():
        if value is not None:
            output[key] = value

    if question.parts:
        output["parts"][0]["content"] = question.parts[0].text
        output["parts"][0]["workedSolution"]["content"] = question.parts[
            0
        ].worked_solution
        for j in range(1, len(question.parts)):
            output["parts"].append(deepcopy(template["parts"][0]))
            output["parts"][j]["content"] = question.parts[j].text
            output["parts"][j]["orderNumber"] = j
            output["parts"][j]["workedSolution"]["content"] = question.parts[
                j
            ].worked_solution

    return output


def converter(
    question_template: dict[str, Any],
    set_template: dict[str, Any],
    SetQuestions: Set,
    output_dir: str,
) -> None:
    """Turns a set of question objects into Lambda Feedback JSON.

    Args:
        question_template: The loaded JSON from the minimal question template (it needs to be in sync).
        set_template: The loaded JSON from the minimal set template (it needs to be in sync).
        SetQuestions: A Set object containing questions.
        output_dir: The absolute path for where to produced the final JSON/zip files.
    """
    ListQuestions = SetQuestions.questions
    set_name = SetQuestions._name
    set_description = SetQuestions._description

    # create directory to put the questions
    os.makedirs(output_dir, exist_ok=True)
    output_question = os.path.join(output_dir, set_name)
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
    with open(f"{output_question}/set_{set_name}.json", "w") as file:
        json.dump(set_template, file)

    for i in range(len(ListQuestions)):
        output = _question_json(ListQuestions[i], i, question_template)

        # Lambda Feedback names the file after the title with only spaces made
        # underscores. Path separators go too, so a title cannot leave the set folder,
        # and so do the characters Windows forbids in file names.
        filename = (
            "question_"
            + str(i).zfill(3)
            + "_"
            + re.sub(r'[\s/\\<>:"|?*]', "_", output["title"].strip())
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

    # check if directory exists in file
    if os.path.isdir(output_dir):
        try:
            shutil.rmtree(output_dir)
        except OSError as e:
            print("Error: %s : %s" % (output_dir, e.strerror))
    converter(question_template, set_template, set_questions, output_dir)


def load(path: str) -> Set:
    """Reads a Lambda Feedback export into a Set, keeping only what the model holds.

    That is the set's name, description and visibilities, and each question's title,
    main text, parts, worked solutions, images and settings.

    A zip is extracted to a new temporary directory, which is left for the operating
    system to clear: the loaded images point into it and must still exist when the
    set is written out.

    Args:
        path: An exported set, as a folder or a zip, with or without a top-level folder.

    Returns:
        The set, with each question's images as absolute paths into ``media/``.

    Raises:
        ValueError: If the export does not hold exactly one ``set_*.json``.
    """
    root = Path(path)
    if root.suffix == ".zip":
        extracted = tempfile.mkdtemp(prefix="in2lambda-")
        with zipfile.ZipFile(root) as zf:
            zf.extractall(extracted)
        root = Path(extracted)

    set_files = list(root.rglob("set_*.json"))
    if len(set_files) != 1:
        raise ValueError(f"Expected one set_*.json in {path}, found {len(set_files)}")
    (set_file,) = set_files
    export_dir = set_file.parent

    set_json = json.loads(set_file.read_text())
    question_set = Set(
        _name=set_json["name"],
        _description=set_json["description"],
        _finalAnswerVisibility=VisibilityController(
            VisibilityStatus(set_json["finalAnswerVisibility"])
        ),
        _workedSolutionVisibility=VisibilityController(
            VisibilityStatus(set_json["workedSolutionVisibility"])
        ),
        _structuredTutorialVisibility=VisibilityController(
            VisibilityStatus(set_json["structuredTutorialVisibility"])
        ),
    )

    question_files = sorted(
        export_dir.glob("question_*.json"),
        key=lambda file: json.loads(file.read_text())["orderNumber"],
    )
    media = sorted((export_dir / "media").glob("*"))
    for question_file in question_files:
        question_json = json.loads(question_file.read_text())
        parts = [
            Part(
                text=part["content"],
                worked_solution=(
                    part["workedSolution"]["content"]
                    if "workedSolution" in part
                    else ""
                ),
            )
            for part in question_json["parts"]
        ]
        question_set.questions.append(
            Question(
                title=question_json["title"],
                main_text=question_json["masterContent"],
                parts=parts,
                images=[
                    str(image)
                    for image in media
                    if image.name.startswith(f"{question_file.stem}_")
                ],
                # Every loaded part already has its text and solution, so further
                # add_part_text/add_solution calls must add parts after them rather
                # than overwrite the first.
                _last_part={"solution": len(parts), "text": len(parts)},
                skill=question_json.get("skill"),
                guidance=question_json.get("guidance"),
                duration_lower_bound=question_json.get("durationLowerBound"),
                duration_upper_bound=question_json.get("durationUpperBound"),
                publish=question_json["publish"],
                display_final_answer=question_json["displayFinalAnswer"],
                display_worked_solution=question_json["displayWorkedSolution"],
                display_structured_tutorial=question_json["displayStructuredTutorial"],
                display_chatbot=question_json["displayChatbot"],
            )
        )
    return question_set
