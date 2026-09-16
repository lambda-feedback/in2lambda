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


def _post(pdf_id="abc123", error=None):
    post = MagicMock(status_code=200)
    post.json.return_value = {"error": error} if error else {"pdf_id": pdf_id}
    return post


def _status(status, error=None):
    body = {"status": status}
    if error:
        body["error"] = error
    resp = MagicMock(status_code=200)
    resp.json.return_value = body
    return resp


def test_pdf_to_markdown_returns_markdown_and_localises_figures(tmp_path):
    pdf = _pdf(tmp_path)
    out_dir = tmp_path / "out"

    completed = _status("completed")
    md = MagicMock(
        status_code=200,
        text="# Heading\n\n![](https://cdn.mathpix.com/x/fig.png?width=8) done\n",
    )
    image = MagicMock(status_code=200, content=b"PNGBYTES")

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = _post()
        req.get.side_effect = [completed, md, image]
        markdown = pdf_to_markdown(str(pdf), str(out_dir), poll_interval=0.0)

    assert "![pictureTag](./media/0_fig.png)" in markdown
    assert not (out_dir / "paper.md").exists()
    assert (out_dir / "media" / "0_fig.png").read_bytes() == b"PNGBYTES"


def test_pdf_to_markdown_polls_until_ready(tmp_path):
    pdf = _pdf(tmp_path)

    processing = _status("processing")
    completed = _status("completed")
    md = MagicMock(status_code=200, text="# Only text, no figures\n")

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = _post()
        req.get.side_effect = [processing, processing, completed, md]
        markdown = pdf_to_markdown(
            str(pdf), str(tmp_path / "out"), poll_interval=0.0, max_polls=5
        )

    assert markdown.startswith("# Only text")


def test_pdf_to_markdown_times_out(tmp_path):
    pdf = _pdf(tmp_path)

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = _post()
        req.get.return_value = _status("processing")
        with pytest.raises(RuntimeError, match="did not finish"):
            pdf_to_markdown(
                str(pdf), str(tmp_path / "out"), poll_interval=0.0, max_polls=3
            )


def test_pdf_to_markdown_raises_on_rejected_upload(tmp_path):
    pdf = _pdf(tmp_path)

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = _post(error="Invalid file type")
        with pytest.raises(RuntimeError, match="Mathpix rejected the PDF"):
            pdf_to_markdown(str(pdf), str(tmp_path / "out"))


def test_pdf_to_markdown_raises_immediately_on_conversion_error(tmp_path):
    pdf = _pdf(tmp_path)

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = _post()
        req.get.return_value = _status("error", error="conversion failed")
        with pytest.raises(RuntimeError, match="conversion failed"):
            pdf_to_markdown(
                str(pdf), str(tmp_path / "out"), poll_interval=0.0, max_polls=60
            )

    # Only the single status poll should have happened, not all 60.
    assert req.get.call_count == 1


def test_pdf_to_markdown_warns_on_failed_figure_download(tmp_path):
    pdf = _pdf(tmp_path)
    out_dir = tmp_path / "out"

    completed = _status("completed")
    md = MagicMock(
        status_code=200,
        text="![](https://cdn.mathpix.com/x/fig.png) done\n",
    )
    image = MagicMock(status_code=404, content=b"")

    with patch("in2lambda.wizard.mathpix.requests") as req:
        req.post.return_value = _post()
        req.get.side_effect = [completed, md, image]
        with pytest.warns(UserWarning, match="figure download failed"):
            markdown = pdf_to_markdown(str(pdf), str(out_dir), poll_interval=0.0)

    assert "https://cdn.mathpix.com/x/fig.png" in markdown
    assert not (out_dir / "media" / "0_fig.png").exists()


def test_missing_credentials_raise(tmp_path, monkeypatch):
    monkeypatch.delenv("MATHPIX_APP_ID", raising=False)
    monkeypatch.delenv("MATHPIX_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="MATHPIX_APP_ID"):
        pdf_to_markdown(str(_pdf(tmp_path)), str(tmp_path / "out"))
