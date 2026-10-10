"""Converts questions from a Python set object into Lambda Feedback JSON."""

import json
import os
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from in2lambda.api.part import Branch, Part
from in2lambda.api.response_area import Case, ResponseArea
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


def _case_to_json(case: Case) -> dict[str, Any]:
    output = {
        "id": case.id,
        "answer": case.answer,
        "feedback": case.feedback,
        "isCorrect": case.is_correct,
        "params": case.params,
    }
    if case.color is not None:
        output["color"] = case.color.value
    return output


def _response_area_to_json(area: ResponseArea, order: int) -> dict[str, Any]:
    output = {
        "orderNumber": order,
        "contentAfter": area.content_after,
        "preResponseText": area.pre_text,
        "postResponseText": area.post_text,
        "inputSymbols": [
            {
                "symbol": symbol.symbol,
                "code": symbol.code,
                "aliases": symbol.aliases,
                "isVisible": symbol.is_visible,
            }
            for symbol in area.input_symbols
        ],
        "displayInputSymbols": area.display_input_symbols,
        "includeInPdf": area.include_in_pdf,
        "saveAllowed": area.save_allowed,
        "evaluationFunctionName": area.evaluation_function,
        "livePreview": area.live_preview,
        "gradeParams": area._grade_params(),
        "separateFeedback": area.separate_feedback,
        "commonFeedbackColor": area.common_feedback_color,
        "correctFeedbackColor": area.correct_feedback_color,
        "correctFeedbackPrefix": area.correct_feedback_prefix,
        "incorrectFeedbackColor": area.incorrect_feedback_color,
        "incorrectFeedbackPrefix": area.incorrect_feedback_prefix,
        "tests": [
            {
                "id": test.id,
                "payload": test.payload,
                "expectedResponse": {"isCorrect": test.is_correct},
            }
            for test in area.tests
        ],
        "cases": [_case_to_json(case) for case in area.cases],
        "response": {
            "responseInput": {
                "responseType": area.response_type,
                "answer": area.answer,
                "config": area._config(),
            }
        },
    }
    if area.check_button_text:
        output["checkButtonText"] = area.check_button_text
    return output


def _branch_to_json(branch: Branch) -> dict[str, Any]:
    return {
        "title": branch.title,
        "content": branch.content,
        "children": [_branch_to_json(child) for child in branch.branches],
    }


def _part_to_json(part: Part, order: int) -> dict[str, Any]:
    output = {
        "orderNumber": order,
        "content": part.content,
        "answerContent": part.answer,
        "responseAreas": [
            _response_area_to_json(area, j)
            for j, area in enumerate(part.response_areas)
        ],
    }
    # Lambda Feedback leaves each key out of a part that has none.
    for key, content, branches in (
        ("tutorial", part.tutorial, part.tutorial_branches),
        ("workedSolution", part.worked_solution, part.worked_solution_branches),
    ):
        if content or branches:
            output[key] = {
                "content": content,
                "children": [_branch_to_json(branch) for branch in branches],
            }
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
    set_template["chatbotVisibility"] = str(SetQuestions._chatbotVisibility.status)
    set_template["isSurvey"] = SetQuestions.is_survey
    set_template["manuallyHidden"] = SetQuestions.manually_hidden
    for key, value in {
        "releasedAt": SetQuestions.released_at,
        "hiddenAt": SetQuestions.hidden_at,
    }.items():
        if value is not None:
            set_template[key] = value
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
        output["masterContent"] = ListQuestions[i].master_content

        question = ListQuestions[i]
        output["publish"] = question.publish
        output["displayFinalAnswer"] = question.display_final_answer
        output["displayWorkedSolution"] = question.display_worked_solution
        output["displayStructuredTutorial"] = question.display_structured_tutorial
        output["displayChatbot"] = question.display_chatbot
        # An unset optional setting is left out of the JSON, so that in2lambda writes no
        # value the author did not choose.
        for key, value in {
            "skill": question.skill,
            "guidance": question.guidance,
            "durationLowerBound": question.duration_lower_bound,
            "durationUpperBound": question.duration_upper_bound,
        }.items():
            if value is not None:
                output[key] = value

        if question.parts:
            output["parts"] = [
                _part_to_json(part, j) for j, part in enumerate(question.parts)
            ]

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

    # check if directory exists in file
    if os.path.isdir(output_dir):
        try:
            shutil.rmtree(output_dir)
        except OSError as e:
            print("Error: %s : %s" % (output_dir, e.strerror))
    converter(question_template, set_template, set_questions, output_dir)
