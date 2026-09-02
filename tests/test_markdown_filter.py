"""Tests for the ``Markdown`` filter (hand-authored ``#``/``##`` question sets)."""

import json
import os

from in2lambda.main import runner


def _example(filters_dir: str) -> str:
    return os.path.join(filters_dir, "Markdown", "example.md")


def test_example_parses_into_questions_parts_and_solutions(filters_dir: str) -> None:
    result = runner(_example(filters_dir), "Markdown")

    assert [q.title for q in result.questions] == [
        "Projectile motion",
        "Newton’s second law",
    ]

    projectile = result.questions[0]
    assert projectile.main_text.startswith("A ball is thrown horizontally")
    assert [p.text for p in projectile.parts] == [
        "How long does the ball take to reach the ground?",
        "How far from the launch point does the ball land?",
    ]
    assert projectile.parts[0].worked_solution.startswith("Vertical motion is")
    assert "v_0 t" in projectile.parts[1].worked_solution

    # A question with no ``##`` parts keeps its solution on a single empty part.
    newton = result.questions[1]
    assert newton.parts[0].text == ""
    assert "F = m a" in newton.parts[0].worked_solution


def test_markdown_filter_writes_importable_json(filters_dir: str, tmp_path) -> None:
    out_dir = tmp_path / "out"
    runner(_example(filters_dir), "Markdown", str(out_dir))

    question_files = sorted((out_dir / "set").glob("question_*.json"))
    assert len(question_files) == 2
    first = json.loads(question_files[0].read_text())
    assert first["title"] == "Projectile motion"
    assert (
        first["parts"][0]["content"]
        == "How long does the ball take to reach the ground?"
    )
    assert first["parts"][0]["workedSolution"]["content"].startswith(
        "Vertical motion is"
    )


def test_bad_math_delimiters_warn_but_do_not_fail(tmp_path, capsys) -> None:
    bad = tmp_path / "bad.md"
    bad.write_text("# Q\n\nText with a stray $ sign and no closing delimiter")

    result = runner(str(bad), "Markdown")

    assert result.questions[0].title == "Q"
    assert "unclosed inline" in capsys.readouterr().out


_RA_BLOCK = (
    "# Circle\n\n"
    "## Circumference\n\n"
    "Give the circumference for $d = 10$.\n\n"
    "## Solution\n\n"
    "$31.4159$.\n\n"
    "```lambda-feedback\n"
    '{"responseType": "EXPRESSION", "answer": "3.14159 * 10", '
    '"evaluationFunction": "compareExpressions", '
    '"gradeParams": {"rtol": 0.001}}\n'
    "```\n"
)


def test_lambda_feedback_block_becomes_a_response_area(tmp_path) -> None:
    md = tmp_path / "q.md"
    md.write_text(_RA_BLOCK)

    part = runner(str(md), "Markdown").questions[0].parts[0]

    assert part.text == "Give the circumference for $d = 10$."
    assert part.worked_solution == "$31.4159$."
    assert len(part.response_areas) == 1
    response_area = part.response_areas[0]
    assert response_area.response_type == "EXPRESSION"
    assert response_area.answer == "3.14159 * 10"
    assert response_area.evaluation_function == "compareExpressions"
    assert response_area.grade_params == {"rtol": 0.001}


def test_lambda_feedback_block_survives_to_json(tmp_path) -> None:
    md = tmp_path / "q.md"
    md.write_text(_RA_BLOCK)
    out_dir = tmp_path / "out"
    runner(str(md), "Markdown", str(out_dir))

    question = json.loads(next((out_dir / "set").glob("question_*.json")).read_text())
    area = question["parts"][0]["responseAreas"][0]
    assert area["evaluationFunctionName"] == "compareExpressions"
    assert area["response"]["responseInput"]["answer"] == "3.14159 * 10"


def test_malformed_lambda_feedback_block_warns_but_converts(tmp_path, capsys) -> None:
    md = tmp_path / "q.md"
    md.write_text(
        "# Q\n\n## Part\n\ntext\n\n## Solution\n\nsol\n\n"
        "```lambda-feedback\n{ not valid json }\n```\n"
    )

    result = runner(str(md), "Markdown")

    assert result.questions[0].parts[0].response_areas == []
    assert "lambda-feedback block is not valid JSON" in capsys.readouterr().out


def test_separate_answers_file_fills_worked_solutions(tmp_path) -> None:
    questions = tmp_path / "q.md"
    questions.write_text("# Q1\n\nFirst question.\n\n# Q2\n\nSecond question.\n")
    answers = tmp_path / "a.md"
    answers.write_text("# Q1\n\nAnswer to one.\n\n# Q2\n\nAnswer to two.\n")

    result = runner(str(questions), "Markdown", answer_file=str(answers))

    assert result.questions[0].parts[0].worked_solution == "Answer to one."
    assert result.questions[1].parts[0].worked_solution == "Answer to two."
