"""Converts questions between a Python set object and Lambda Feedback JSON."""

import json
import os
import re
import shutil
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.response_area import Case, InputSymbol, ResponseArea, Test
from in2lambda.api.set import Set
from in2lambda.api.visibility_status import VisibilityController, VisibilityStatus

MINIMAL_QUESTION_TEMPLATE = "minimal_template_question.json"
MINIMAL_SET_TEMPLATE = "minimal_template_set.json"

_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
"""A markdown image, e.g. ``![pictureTag](question_000_Title_0001.png)``."""


def _image_for(reference: str, images: list[str]) -> Optional[str]:
    """Which of a question's images a markdown reference names.

    An image is matched by file name, which is the link between a reference and a file: a
    filter resolves the path it writes into the markdown, and Lambda Feedback finds an
    image in ``media/`` by its file name alone. Where a question lists two files of the
    same name, the rest of the reference decides, by naming the end of one of their paths.

    Returns:
        The image, or None where the question lists no image of that name. The writer
        then writes the reference as it stands, and :mod:`in2lambda.validation` reports
        it.
    """
    named = [image for image in images if Path(image).name == Path(reference).name]
    if len(named) > 1:
        # A filter writes the reference as the document wrote it and normalises the path
        # it lists beside it, so a `..` appears on one side only and comes off for the
        # two to match. ``pathlib`` has already dropped a `.`.
        parts = tuple(part for part in Path(reference).parts if part != "..")
        named = [
            image for image in named if Path(image).parts[-len(parts) :] == parts
        ] or named
    return named[0] if named else None


def _templates() -> tuple[dict[str, Any], dict[str, Any]]:
    """Loads the minimal question and set templates that the writer fills in.

    Returns:
        The question template and the set template.
    """
    # An absolute path, so that the templates are found whatever the working directory is.
    with open(Path(__file__).with_name(MINIMAL_QUESTION_TEMPLATE), "r") as file:
        question_template = json.load(file)

    with open(Path(__file__).with_name(MINIMAL_SET_TEMPLATE), "r") as file:
        set_template = json.load(file)

    return question_template, set_template


def _zip(files: list[Path], root: Path, zip_path: str) -> None:
    """Zips the given files, keeping where they sit relative to a folder.

    The archive lists only the files this run wrote, so whatever else the folder holds is
    left out of the upload and left on disk.

    Args:
        files: The files to include, all inside root.
        root: The folder the archive names are relative to.
        zip_path: The path to create the zip file at.
    """
    # Sorted by archive name, so that the zip lists its files in one order, and each file
    # is named once: a file written twice is one file on disk.
    names = sorted({str(file.relative_to(root)): file for file in files}.items())
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, file in names:
            zf.write(file, arcname=name)


def _response_area_to_json(area: ResponseArea, order: int) -> dict[str, Any]:
    return {
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
        "gradeParams": area.grade_params,
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
        "cases": [
            {
                "id": case.id,
                "answer": case.answer,
                "feedback": case.feedback,
                "isCorrect": case.is_correct,
                "params": case.params,
            }
            for case in area.cases
        ],
        "response": {
            "responseInput": {
                "responseType": area.response_type,
                "answer": area.answer,
                "config": area.config,
            }
        },
    }


def _response_area_from_json(area: dict[str, Any]) -> ResponseArea:
    response = area["response"]["responseInput"]
    return ResponseArea(
        response_type=response["responseType"],
        answer=response["answer"],
        config=response["config"],
        evaluation_function=area["evaluationFunctionName"],
        grade_params=area["gradeParams"],
        pre_text=area["preResponseText"],
        post_text=area["postResponseText"],
        content_after=area["contentAfter"],
        input_symbols=[
            InputSymbol(
                symbol=symbol["symbol"],
                code=symbol["code"],
                aliases=symbol["aliases"],
                is_visible=symbol["isVisible"],
            )
            for symbol in area["inputSymbols"]
        ],
        display_input_symbols=area["displayInputSymbols"],
        live_preview=area["livePreview"],
        include_in_pdf=area["includeInPdf"],
        save_allowed=area["saveAllowed"],
        separate_feedback=area["separateFeedback"],
        common_feedback_color=area["commonFeedbackColor"],
        correct_feedback_color=area["correctFeedbackColor"],
        correct_feedback_prefix=area["correctFeedbackPrefix"],
        incorrect_feedback_color=area["incorrectFeedbackColor"],
        incorrect_feedback_prefix=area["incorrectFeedbackPrefix"],
        tests=[
            Test(
                payload=test["payload"],
                is_correct=test["expectedResponse"]["isCorrect"],
                id=test["id"],
            )
            for test in area["tests"]
        ],
        cases=[
            Case(
                answer=case["answer"],
                feedback=case["feedback"],
                is_correct=case["isCorrect"],
                params=case["params"],
                id=case["id"],
            )
            for case in area["cases"]
        ],
    )


def _part_to_json(
    part: Part, template_part: dict[str, Any], order: int
) -> dict[str, Any]:
    output = deepcopy(template_part)
    output["orderNumber"] = order
    output["content"] = part.text
    output["answerContent"] = part.answer
    output["responseAreas"] = [
        _response_area_to_json(area, j) for j, area in enumerate(part.response_areas)
    ]
    output["workedSolution"]["content"] = part.worked_solution
    return output


def _question_title(question: Question, i: int) -> str:
    return question.title if question.title != "" else f"Question {i + 1}"


def _question_stem(i: int, title: str) -> str:
    # Lambda Feedback names the file after the title, with spaces replaced by
    # underscores. Path separators are replaced too, so that a title cannot leave the set
    # folder, as are the characters Windows forbids in a file name.
    return (
        "question_"
        + str(i).zfill(3)
        + "_"
        + re.sub(r'[\s/\\<>:"|?*]', "_", title.strip())
    )


def _question_json(
    question: Question, i: int, template: dict[str, Any]
) -> dict[str, Any]:
    output = deepcopy(template)

    output["orderNumber"] = i  # order number starts at 0
    output["title"] = _question_title(question, i)
    output["masterContent"] = question.main_text

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
            _part_to_json(part, template["parts"][0], j)
            for j, part in enumerate(question.parts)
        ]

    return output


def _media_name(image: str, stem: str, taken: set[str]) -> str:
    """The name an image is written under in ``media/``, which is one flat folder.

    The image's own file name, or, where another file holds that name, the name Lambda
    Feedback's own exports give an image: the question's name, numbered.
    """
    name = Path(image).name
    if name not in taken:
        return name
    number = 1
    while (numbered := f"{stem}_{number:04}{Path(image).suffix}") in taken:
        number += 1
    return numbered


def _with_media_names(value: Any, question: Question, media: dict[str, str]) -> Any:
    """A question's JSON with every image reference in it rewritten to its media name.

    This function walks the JSON instead of reading named fields, because a reference can
    be written in any markdown the question holds: its text, a part's text, a worked
    solution, a final answer, an answer box's wording or one of its options. A second
    list of those fields here would drift from the list :mod:`in2lambda.validation`
    already checks.
    """
    if isinstance(value, dict):
        return {
            key: _with_media_names(item, question, media) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_with_media_names(item, question, media) for item in value]
    if not isinstance(value, str):
        return value

    def rewrite(reference: re.Match[str]) -> str:
        image = _image_for(reference[1], question.images)
        if image is None:
            return reference[0]
        # Only the path is replaced, because the alt text beside it may read the same.
        name = media[os.path.abspath(image)]
        return reference[0][: reference.start(1) - reference.start()] + name + ")"

    return _IMAGE.sub(rewrite, value)


def _write_question(
    question: Question,
    i: int,
    template: dict[str, Any],
    folder: Path,
    media: dict[str, str],
) -> list[Path]:
    """Writes one question's JSON, and any images it uses, into an existing folder.

    Args:
        question: The question to write.
        i: Its order number, which also prefixes the file name.
        template: The loaded JSON from the minimal question template.
        folder: The folder to write into.
        media: The images the export has copied into ``media/`` so far, each image's path
            on disk against the name it was written under. This function adds the
            question's images to it, so that a file two questions use is one file under
            one name.

    Returns:
        The files written.
    """
    output = _question_json(question, i, template)
    stem = _question_stem(i, output["title"])

    written = []
    for image in question.images:
        path = os.path.abspath(image)
        if path in media:
            continue
        media[path] = _media_name(path, stem, set(media.values()))
        # A media folder is created only for a question that holds an image.
        (folder / "media").mkdir(exist_ok=True)
        written.append(Path(shutil.copy(path, folder / "media" / media[path])))

    json_file = folder / f"{stem}.json"
    with open(json_file, "w") as file:
        json.dump(_with_media_names(output, question, media), file)

    return [json_file] + written


def write_question(question: Question, output_dir: str, number: int = 0) -> None:
    """Writes a single question as its own Lambda Feedback import.

    The question is written to a folder named after it, holding the question's JSON and
    its images under ``media``, and to a zip of that folder. The folder holds no set
    file, because Lambda Feedback imports one question into a set that already exists.

    Args:
        question: The question to write.
        output_dir: Where to put the question's folder and zip.
        number: The question's order number, which also prefixes its file names.
    """
    question_template, _ = _templates()

    folder = Path(output_dir) / _question_stem(
        number, _question_title(question, number)
    )
    folder.mkdir(parents=True, exist_ok=True)
    written = _write_question(question, number, question_template, folder, {})
    _zip(written, folder, f"{folder}.zip")


def converter(
    question_template: dict[str, Any],
    set_template: dict[str, Any],
    SetQuestions: Set,
    output_dir: str,
) -> None:
    """Turns a set of question objects into Lambda Feedback JSON.

    Args:
        question_template: The JSON loaded from the minimal question template.
        set_template: The JSON loaded from the minimal set template.
        SetQuestions: The set of questions to write.
        output_dir: Where to write the JSON and zip files.
    """
    ListQuestions = SetQuestions.questions
    set_name = SetQuestions._name
    set_description = SetQuestions._description

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
    folder = Path(output_question)
    set_file = folder / f"set_{set_name}.json"
    with open(set_file, "w") as file:
        json.dump(set_template, file)

    written = [set_file]
    # Named across the whole set, because media/ is one folder for every question.
    media: dict[str, str] = {}
    for i, question in enumerate(ListQuestions):
        written += _write_question(question, i, question_template, folder, media)

    _zip(written, folder, output_question + ".zip")


def main(set_questions: Set, output_dir: str) -> None:
    """Loads the templates and writes the set as Lambda Feedback JSON and a zip.

    Args:
        set_questions: The set of questions to write.
        output_dir: Where to write the JSON and zip files.
    """
    question_template, set_template = _templates()
    converter(question_template, set_template, set_questions, output_dir)


def load(path: str) -> Set:
    """Reads a Lambda Feedback export into a Set, keeping only what the model holds.

    That is the set's name, description and visibilities, and each question's title,
    main text, parts, worked solutions, images and settings.

    A zip is extracted into a new temporary directory, which the operating system clears:
    the loaded images point into that directory and must exist when the set is written
    out.

    Args:
        path: An exported set, as a folder or a zip, with or without a top-level folder.

    Returns:
        The set, with each question's images as absolute paths into ``media/``.

    Raises:
        ValueError: the export does not hold one ``set_*.json``.
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
                answer=part["answerContent"],
                # An export does not always list areas in order, and an area's
                # contentAfter leads into the area numbered after it.
                response_areas=[
                    _response_area_from_json(area)
                    for area in sorted(
                        part["responseAreas"], key=lambda area: area["orderNumber"]
                    )
                ],
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
                # Every loaded part holds its text and its solution, so a later
                # add_part_text or add_solution call appends a part instead of
                # overwriting the first.
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
