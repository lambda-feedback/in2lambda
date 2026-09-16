"""Tests for ``in2lambda wizard``: extraction is mocked, no network calls."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from in2lambda.main import runner
from in2lambda.wizard.extract import WizardPart, WizardQuestion, WizardSet, to_markdown

SAMPLE_SET = WizardSet(
    questions=[
        WizardQuestion(
            title="Projectile",
            text="A ball is thrown from height $h$.",
            parts=[
                WizardPart(text="Find the flight time.", solution="$t=\\sqrt{2h/g}$."),
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

# A question with both per-part solutions and a closing overall solution: the
# Markdown filter has no separate slot for a question-level solution once a
# question has parts, so `to_markdown` must fold the overall solution into the
# last part rather than drop it.
SAMPLE_WITH_CLOSING_SOLUTION = WizardSet(
    questions=[
        WizardQuestion(
            title="Circuit",
            text="A resistor and capacitor are connected in series.",
            parts=[
                WizardPart(text="Find the time constant.", solution="$\\tau = RC$."),
                WizardPart(
                    text="Find the charge at $t=\\tau$.", solution="$Q = Q_0/e$."
                ),
            ],
            solution="Check units throughout: $\\tau$ has units of seconds.",
        )
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


def test_to_markdown_folds_closing_solution_into_last_part():
    md_file_text = to_markdown(SAMPLE_WITH_CLOSING_SOLUTION)

    # One "## Solution" heading per part (as usual) - no extra, ambiguous
    # heading is emitted for the question-level solution. Its text is instead
    # folded into the last part's, since that's the only heading the Markdown
    # filter would attribute it to anyway.
    assert md_file_text.count("## Solution") == 2
    assert (
        "$Q = Q_0/e$.\n\nCheck units throughout: $\\tau$ has units of seconds."
        in md_file_text
    )


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
    # The extracted markdown must feed straight back into the Markdown filter.
    assert len(runner(str(out), "Markdown").questions) == 2


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


def test_run_wizard_loads_client_before_running_ocr(tmp_path, monkeypatch):
    # get_client() is what loads .env and validates OPENROUTER_API_KEY - it must
    # run before the (paid) Mathpix OCR call, not after, so a missing key is
    # caught before it's spent.
    from in2lambda.wizard import run as run_module

    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    call_order = []

    def fake_pdf_to_markdown(src, out_dir):
        call_order.append("pdf_to_markdown")
        path = tmp_path / "out" / "paper.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# raw ocr\n\nstuff")
        return path

    def fake_get_client():
        call_order.append("get_client")
        return _fake_client(SAMPLE_SET)

    monkeypatch.setattr(run_module, "pdf_to_markdown", fake_pdf_to_markdown)
    monkeypatch.setattr(run_module, "get_client", fake_get_client)
    monkeypatch.setattr(run_module, "resolve_model", lambda value: "test/model")

    run_module.run_wizard(str(pdf), str(tmp_path / "out" / "reviewed.md"))

    assert call_order == ["get_client", "pdf_to_markdown"]


def test_extract_set_raises_when_model_returns_nothing():
    from in2lambda.wizard.extract import extract_set

    client = MagicMock()
    client.beta.chat.completions.parse.return_value.choices = [
        SimpleNamespace(message=SimpleNamespace(parsed=None))
    ]

    with pytest.raises(RuntimeError, match="parseable"):
        extract_set("anything", client, "test/model")


def test_extract_set_repairs_json_unescaped_latex_commands():
    from in2lambda.wizard.extract import extract_set

    # A model that under-escapes "\text"/"\frac"/"\beta"/"\rho" in its structured
    # output lands a bare TAB/FF/BS/CR glued to the rest of the command here.
    mangled = WizardSet(
        questions=[
            WizardQuestion(
                title="Units and symbols",
                text="Height $h = 45\\,\text{m}$ at angle $\theta$.",  # TAB from \t
                parts=[
                    WizardPart(
                        text="State the coefficient.\nKeep this newline.",
                        solution="$\frac12$ with $\beta$ and $\rho$.",  # FF, BS, CR
                    )
                ],
            )
        ]
    )

    result = extract_set("anything", _fake_client(mangled), "test/model")
    question = result.questions[0]

    assert question.text == "Height $h = 45\\,\\text{m}$ at angle $\\theta$."
    assert question.parts[0].solution == "$\\frac12$ with $\\beta$ and $\\rho$."
    # Real newlines must survive - only control chars glued to letters are touched.
    assert question.parts[0].text == "State the coefficient.\nKeep this newline."
