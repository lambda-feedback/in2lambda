"""Converts questions from a Python set object into Lambda Feedback JSON."""

import json
import os
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from in2lambda.api.set import Set

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
    # create the set file
    with open(f"{output_question}/set_{set_name}.json", "w") as file:
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
            output["parts"][0]["content"] = ListQuestions[i].parts[0].text
            output["parts"][0]["workedSolution"]["content"] = (
                ListQuestions[i].parts[0].worked_solution
            )
            for j in range(1, len(ListQuestions[i].parts)):
                output["parts"].append(deepcopy(question_template["parts"][0]))
                output["parts"][j]["content"] = ListQuestions[i].parts[j].text
                output["parts"][j]["orderNumber"] = j
                output["parts"][j]["workedSolution"]["content"] = (
                    ListQuestions[i].parts[j].worked_solution
                )

        # Output file
        filename = (
            "question_" + str(i).zfill(3) + "_" + output["title"].replace(" ", "_")
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
