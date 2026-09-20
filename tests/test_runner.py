"""End-to-end tests for :func:`in2lambda.main.runner` across the built-in filters.

Each built-in filter ships a self-contained ``example.tex`` that exercises the
document structure it targets. These tests find every filter in the package, run
it over its own example and check both the in-memory :class:`~in2lambda.api.set.Set`
and the JSON/ZIP files written to disk, so a filter shipped without an example fails.
"""

import json
import os

import pytest
from click.testing import CliRunner

from in2lambda.api.set import Set
from in2lambda.filters import builtin_filters
from in2lambda.main import cli, runner


def _example(filters_dir: str, filter_name: str) -> str:
    path = os.path.join(filters_dir, filter_name, "example.tex")
    assert os.path.isfile(path), f"{filter_name} ships no example.tex to test it with"
    return path


@pytest.mark.parametrize("filter_name", builtin_filters())
def test_runner_returns_populated_set(filter_name: str, filters_dir: str) -> None:
    """Every filter turns its example into a Set with at least one usable question."""
    result = runner(_example(filters_dir, filter_name), filter_name)

    assert isinstance(result, Set)
    assert result.questions, f"{filter_name} produced no questions"
    for question in result.questions:
        # A question is only useful if it has top-level text or at least one part.
        assert question.main_text or question.parts


@pytest.mark.parametrize("filter_name", builtin_filters())
def test_runner_writes_importable_json(
    filter_name: str, filters_dir: str, tmp_path
) -> None:
    """Passing an output directory produces the Lambda Feedback set/ dir and zip."""
    out_dir = tmp_path / "out"
    result = runner(_example(filters_dir, filter_name), filter_name, str(out_dir))

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


def test_cli_reports_problems_and_exports_anyway(tmp_path) -> None:
    """A problem is printed, and is a warning rather than a refusal to export."""
    question_file = tmp_path / "questions.tex"
    question_file.write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\section{Buoyancy}\n"
        "The apparatus is shown in \\includegraphics{absent.png}.\n"
        "\\end{document}\n"
    )
    out_dir = tmp_path / "out"

    result = CliRunner().invoke(
        cli, [str(question_file), "PartsOneSol", "-o", str(out_dir)]
    )

    assert result.exit_code == 0
    assert (
        'Warning: Question 1 "", main text: '
        "the export will not contain the image absent.png" in result.output
    )
    assert (out_dir / "set.zip").is_file()
