"""End-to-end tests for :func:`in2lambda.main.runner` across the built-in filters.

Each built-in filter ships a self-contained ``example.tex`` that exercises the
document structure it targets. These tests run every filter over its own example
and check both the in-memory :class:`~in2lambda.api.set.Set` and the JSON/ZIP
files written to disk.
"""

import json
import os

import pytest

from in2lambda.api.set import Set
from in2lambda.main import runner

BUILTIN_FILTERS = ["PartsSepSol", "PartsOneSol", "PartPartSolSol", "PartSolPartSol"]


@pytest.mark.parametrize("filter_name", BUILTIN_FILTERS)
def test_runner_returns_populated_set(filter_name: str, filters_dir: str) -> None:
    """Every filter turns its example into a Set with at least one usable question."""
    result = runner(os.path.join(filters_dir, filter_name, "example.tex"), filter_name)

    assert isinstance(result, Set)
    assert result.questions, f"{filter_name} produced no questions"
    for question in result.questions:
        # A question is only useful if it has top-level text or at least one part.
        assert question.main_text or question.parts


@pytest.mark.parametrize("filter_name", BUILTIN_FILTERS)
def test_runner_writes_importable_json(
    filter_name: str, filters_dir: str, tmp_path
) -> None:
    """Passing an output directory produces the Lambda Feedback set/ dir and zip."""
    out_dir = tmp_path / "out"
    result = runner(
        os.path.join(filters_dir, filter_name, "example.tex"),
        filter_name,
        str(out_dir),
    )

    set_dir = out_dir / "set"
    assert set_dir.is_dir()
    assert (out_dir / "set.zip").is_file()

    set_json = json.loads((set_dir / "set_set.json").read_text())
    assert set_json["name"] == "set"

    question_files = sorted(set_dir.glob("question_*.json"))
    assert len(question_files) == len(result.questions)
    for question_file in question_files:
        question_json = json.loads(question_file.read_text())
        assert question_json["title"]
        assert "masterContent" in question_json
        assert "parts" in question_json
