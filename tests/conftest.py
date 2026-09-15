"""Shared pytest fixtures for the in2lambda test suite."""

import json
import os
from pathlib import Path

import pytest

import in2lambda
from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.set import Set
from in2lambda.api.visibility_status import VisibilityController, VisibilityStatus

EXPORTS_DIR = Path(__file__).parent / "fixtures" / "exports"
"""Real Lambda Feedback exports, one set per folder, exactly as the platform wrote them."""

EXPORTS = sorted(path for path in EXPORTS_DIR.iterdir() if path.is_dir())
"""Every export folder, found rather than listed so that adding one needs no code."""


@pytest.fixture(scope="session")
def filters_dir() -> str:
    """Absolute path to the packaged ``filters`` directory.

    Each filter ships a self-contained ``example.tex`` used by the end-to-end tests.
    """
    return os.path.join(os.path.dirname(in2lambda.__file__), "filters")


def load_export(export_dir: Path) -> Set:
    """Reads an exported set into the in2lambda model, keeping only what the model holds.

    The layout followed is the one described in ``fixtures/exports/README.md``.

    Args:
        export_dir: A folder holding one exported set.

    Returns:
        The set, with each question's images as absolute paths into ``media/``.
    """
    (set_file,) = export_dir.glob("set_*.json")
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
        key=lambda path: json.loads(path.read_text())["orderNumber"],
    )
    media = sorted((export_dir / "media").glob("*"))
    for question_file in question_files:
        question_json = json.loads(question_file.read_text())
        question_set.questions.append(
            Question(
                title=question_json["title"],
                main_text=question_json["masterContent"],
                parts=[
                    Part(
                        text=part["content"],
                        worked_solution=(
                            part["workedSolution"]["content"]
                            if "workedSolution" in part
                            else ""
                        ),
                    )
                    for part in question_json["parts"]
                ],
                images=[
                    str(image)
                    for image in media
                    if image.name.startswith(f"{question_file.stem}_")
                ],
            )
        )
    return question_set
