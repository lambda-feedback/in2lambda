"""Tests for ``in2lambda wizard``: extraction is mocked, no network calls."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from in2lambda.main import runner
from in2lambda.wizard.confirm import confirm_response_areas
from in2lambda.wizard.extract import (
    WizardPart,
    WizardQuestion,
    WizardResponseArea,
    WizardSet,
    to_markdown,
)


def _ra(answer: str) -> WizardResponseArea:
    return WizardResponseArea(
        response_type="EXPRESSION",
        answer=answer,
        evaluation_function="compareExpressions",
        reasoning="symbolic answer",
    )


SAMPLE_SET = WizardSet(
    questions=[
        WizardQuestion(
            title="Projectile",
            text="A ball is thrown from height $h$.",
            parts=[
                WizardPart(
                    text="Find the flight time.",
                    solution="$t=\\sqrt{2h/g}$.",
                    response_area=_ra("sqrt(2*h/g)"),
                ),
                WizardPart(text="Find the range.", solution="$x=v_0 t$."),
            ],
        ),
        WizardQuestion(
            title="Newton's second law",
            text="State the law.",
            solution="$F = ma$.",
        ),
    ]
)


def _fake_client(question_set: WizardSet) -> MagicMock:
    client = MagicMock()
    client.beta.chat.completions.parse.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(parsed=question_set))
    ]
    return client


def test_to_markdown_roundtrips_through_markdown_filter(tmp_path):
    md_file = tmp_path / "wizard.md"
    md_file.write_text(to_markdown(SAMPLE_SET))

    result = runner(str(md_file), "Markdown")

    assert [q.title for q in result.questions] == ["Projectile", "Newton’s second law"]
    projectile = result.questions[0]
    assert projectile.main_text == "A ball is thrown from height $h$."
    assert [p.text for p in projectile.parts] == [
        "Find the flight time.",
        "Find the range.",
    ]
    assert projectile.parts[0].worked_solution == "$t=\\sqrt{2h/g}$."
    assert result.questions[1].parts[0].worked_solution == "$F = ma$."

    # The proposed response area round-trips as a lambda-feedback block.
    response_area = projectile.parts[0].response_areas[0]
    assert response_area.evaluation_function == "compareExpressions"
    assert response_area.answer == "sqrt(2*h/g)"
    assert projectile.parts[1].response_areas == []


def test_run_wizard_writes_reviewable_markdown(tmp_path, monkeypatch):
    from in2lambda.wizard import run as run_module

    monkeypatch.setattr(run_module, "get_client", lambda: _fake_client(SAMPLE_SET))
    monkeypatch.setattr(run_module, "resolve_model", lambda value: "test/model")

    source = tmp_path / "raw.md"
    source.write_text("some messy notes with a $x$ here")
    out = tmp_path / "out" / "reviewed.md"

    written = run_module.run_wizard(str(source), str(out))

    assert written == out
    text = out.read_text()
    assert text.startswith("# Projectile")
    assert "## Part 1" in text and "## Solution" in text
    # The confirmed response area is written as a lambda-feedback block.
    assert "```lambda-feedback" in text
    assert '"evaluationFunction": "compareExpressions"' in text
    # The extracted markdown must feed straight back into the Markdown filter.
    converted = runner(str(out), "Markdown")
    assert len(converted.questions) == 2
    assert converted.questions[0].parts[0].response_areas[0].answer == "sqrt(2*h/g)"


def test_no_response_areas_flag_drops_them(tmp_path, monkeypatch):
    from in2lambda.wizard import run as run_module

    monkeypatch.setattr(
        run_module, "get_client", lambda: _fake_client(SAMPLE_SET.model_copy(deep=True))
    )
    monkeypatch.setattr(run_module, "resolve_model", lambda value: "test/model")

    source = tmp_path / "raw.md"
    source.write_text("notes")
    out = tmp_path / "draft.md"

    run_module.run_wizard(str(source), str(out), response_areas=False)

    text = out.read_text()
    assert "```lambda-feedback" not in text
    assert runner(str(out), "Markdown").questions[0].parts[0].response_areas == []


def test_confirm_response_areas_strips_when_disabled():
    question_set = SAMPLE_SET.model_copy(deep=True)
    confirm_response_areas(question_set, enabled=False)
    assert question_set.questions[0].parts[0].response_area is None


def test_confirm_response_areas_accept_all_keeps_suggestions():
    question_set = SAMPLE_SET.model_copy(deep=True)
    confirm_response_areas(question_set, accept_all=True)
    assert question_set.questions[0].parts[0].response_area.answer == "sqrt(2*h/g)"


def test_run_wizard_uses_mathpix_for_pdfs(tmp_path, monkeypatch):
    from in2lambda.wizard import run as run_module

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    ocr_markdown = tmp_path / "out" / "paper.md"

    def fake_pdf_to_markdown(src, out_dir):
        path = ocr_markdown
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# raw ocr\n\nstuff")
        return path

    seen = {}

    def fake_extract(source_markdown, client, model):
        seen["source"] = source_markdown
        return SAMPLE_SET

    monkeypatch.setattr(run_module, "pdf_to_markdown", fake_pdf_to_markdown)
    monkeypatch.setattr(run_module, "get_client", lambda: MagicMock())
    monkeypatch.setattr(run_module, "extract_set", fake_extract)

    run_module.run_wizard(str(pdf), str(tmp_path / "out" / "reviewed.md"))

    assert seen["source"] == "# raw ocr\n\nstuff"


def test_extract_set_raises_when_model_returns_nothing():
    from in2lambda.wizard.extract import extract_set

    client = MagicMock()
    client.beta.chat.completions.parse.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(parsed=None))
    ]

    with pytest.raises(RuntimeError, match="parseable"):
        extract_set("anything", client, "test/model")
