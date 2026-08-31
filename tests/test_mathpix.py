"""Tests for the Mathpix PDF -> markdown helper. All HTTP is mocked."""

from unittest.mock import MagicMock, patch

import pytest

from in2lambda.wizard.mathpix import pdf_to_markdown


@pytest.fixture(autouse=True)
def _mathpix_creds(monkeypatch):
    monkeypatch.setenv("MATHPIX_APP_ID", "test-id")
    monkeypatch.setenv("MATHPIX_API_KEY", "test-key")


def _pdf(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return pdf


def test_pdf_to_markdown_writes_md_and_localises_figures(tmp_path):
    pdf = _pdf(tmp_path)
    out_dir = tmp_path / "out"

    post = MagicMock(status_code=200)
    post.json.return_value = {"pdf_id": "abc123"}
    md = MagicMock(
        status_code=200,
        text="# Heading\n\n![](https://cdn.mathpix.com/x/fig.png?width=8) done\n",
    )
    image = MagicMock(status_code=200, content=b"PNGBYTES")

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = post
        req.get.side_effect = [md, image]
        md_path = pdf_to_markdown(str(pdf), str(out_dir), poll_interval=0.0)

    assert md_path == out_dir / "paper.md"
    text = md_path.read_text()
    assert "![pictureTag](./media/0_fig.png)" in text
    assert (out_dir / "media" / "0_fig.png").read_bytes() == b"PNGBYTES"


def test_pdf_to_markdown_polls_until_ready(tmp_path):
    pdf = _pdf(tmp_path)

    post = MagicMock(status_code=200)
    post.json.return_value = {"pdf_id": "abc123"}
    not_ready = MagicMock(status_code=202)
    ready = MagicMock(status_code=200, text="# Only text, no figures\n")

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = post
        req.get.side_effect = [not_ready, not_ready, ready]
        md_path = pdf_to_markdown(
            str(pdf), str(tmp_path / "out"), poll_interval=0.0, max_polls=5
        )

    assert md_path.read_text().startswith("# Only text")


def test_pdf_to_markdown_times_out(tmp_path):
    pdf = _pdf(tmp_path)

    post = MagicMock(status_code=200)
    post.json.return_value = {"pdf_id": "abc123"}

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = post
        req.get.return_value = MagicMock(status_code=202)
        with pytest.raises(RuntimeError, match="did not finish"):
            pdf_to_markdown(
                str(pdf), str(tmp_path / "out"), poll_interval=0.0, max_polls=3
            )


def test_missing_credentials_raise(tmp_path, monkeypatch):
    monkeypatch.delenv("MATHPIX_APP_ID", raising=False)
    monkeypatch.delenv("MATHPIX_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="MATHPIX_APP_ID"):
        pdf_to_markdown(str(_pdf(tmp_path)), str(tmp_path / "out"))
