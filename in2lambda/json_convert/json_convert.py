"""Converts questions from a Python module object into Lambda Feedback JSON."""

import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from in2lambda.api.question import Question

MINIMAL_TEMPLATE = "minimal_template.json"


def converter(
    template: dict[str, Any], ListQuestions: list[Question], output_dir: str
) -> None:
    """Turns a list of question objects into Lambda Feedback JSON.

    Args:
        template: The loaded JSON from the minimal template (it needs to be in sync).
        ListQuestions: A list of question objects.
        output_dir: The absolute path for where to produced the final JSON/zip files.
    """
    # Create output by copying template

    # create directory to put the questions
    os.makedirs(output_dir, exist_ok=True)
    output_question = os.path.join(output_dir, "set")
    os.makedirs(output_question, exist_ok=True)

    # create directory to put images - should be in set
    output_image = os.path.join(output_question, "media")
    os.makedirs(output_image, exist_ok=True)

    for i in range(len(ListQuestions)):
        output = deepcopy(template)

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
                output["parts"].append(deepcopy(template["parts"][0]))
                output["parts"][j]["content"] = ListQuestions[i].parts[j].text
                output["parts"][j]["workedSolution"]["content"] = (
                    ListQuestions[i].parts[j].worked_solution
                )

        # Output file
        filename = "question_" + str(i + 1)

        # write questions into directory
        with open(f"{output_question}/{filename}.json", "w") as file:
            json.dump(output, file)

        # write image into directory
        for k in range(len(ListQuestions[i].images)):
            image_path = os.path.abspath(
                ListQuestions[i].images[k]
            )  # converts computer path into python path
            shutil.copy(image_path, output_image)  # copies image into the directory

        # output zip file in destination folder
        shutil.make_archive(output_question, "zip", output_question)


def main(questions: list[Question], output_dir: str) -> None:
    """Preliminary defensive programming before calling the main converter function.

    This ultimately then produces the Lambda Feedback JSON/ZIP files.

    Args:
        questions: A list of question objects.
        output_dir: Where to output the final Lambda Feedback JSON/ZIP files.
    """
    # Use path so minimal template can be found regardless of where the user is running python from.
    with open(Path(__file__).with_name(MINIMAL_TEMPLATE), "r") as file:
        template = json.load(file)

    # check if directory exists in file
    if os.path.isdir(output_dir):
        try:
            shutil.rmtree(output_dir)
        except OSError as e:
            print("Error: %s : %s" % (output_dir, e.strerror))
    converter(template, questions, output_dir)
