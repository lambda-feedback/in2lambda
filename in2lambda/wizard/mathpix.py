"""Convert a PDF into markdown with the Mathpix OCR API.

Needs ``MATHPIX_APP_ID`` and ``MATHPIX_API_KEY`` in the environment (a ``.env``
file is honoured by the wizard). Figures referenced by the returned markdown are
downloaded next to it so the ``Markdown`` filter can pick them up.
"""

import os
import re
import time
from pathlib import Path

import requests

MATHPIX_PDF_ENDPOINT = "https://api.mathpix.com/v3/pdf"

# Matches ``![alt](https://...)`` image references in Mathpix markdown.
_REMOTE_IMAGE = re.compile(r"!\[.*?\]\((https?://[^)]+)\)")


def _headers() -> dict:
    """Return the Mathpix auth headers, or raise if credentials are missing."""
    app_id = os.getenv("MATHPIX_APP_ID")
    app_key = os.getenv("MATHPIX_API_KEY")
    if not app_id or not app_key:
        raise RuntimeError(
            "MATHPIX_APP_ID and MATHPIX_API_KEY must be set to convert PDFs "
            "(see https://mathpix.com/ocr)."
        )
    return {"app_id": app_id, "app_key": app_key}


def pdf_to_markdown(
    pdf_path: str,
    out_dir: str,
    poll_interval: float = 5.0,
    max_polls: int = 60,
) -> Path:
    """Convert ``pdf_path`` to markdown, writing it and its figures under ``out_dir``.

    Args:
        pdf_path: Path to the source PDF.
        out_dir: Directory to write ``<stem>.md`` and a ``media/`` folder into.
        poll_interval: Seconds to wait between Mathpix "is it ready yet" polls.
        max_polls: How many times to poll before giving up.

    Returns:
        The path to the written markdown file. Figures are saved in
        ``<out_dir>/media/`` and referenced from the markdown as
        ``./media/<name>``.

    Raises:
        RuntimeError: if credentials are missing or Mathpix does not finish in time.
    """
    headers = _headers()
    out = Path(out_dir)
    (out / "media").mkdir(parents=True, exist_ok=True)

    with open(pdf_path, "rb") as pdf:
        response = requests.post(
            MATHPIX_PDF_ENDPOINT, headers=headers, files={"file": pdf}
        )
    response.raise_for_status()
    pdf_id = response.json()["pdf_id"]

    markdown = _poll_for_markdown(pdf_id, headers, poll_interval, max_polls)
    markdown = _localise_figures(markdown, out)

    md_path = out / f"{Path(pdf_path).stem}.md"
    md_path.write_text(markdown, encoding="utf-8")
    return md_path


def _poll_for_markdown(
    pdf_id: str, headers: dict, poll_interval: float, max_polls: int
) -> str:
    """Poll Mathpix until the ``.md`` render of ``pdf_id`` is ready."""
    url = f"{MATHPIX_PDF_ENDPOINT}/{pdf_id}.md"
    for _ in range(max_polls):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        time.sleep(poll_interval)
    raise RuntimeError(f"Mathpix did not finish converting {pdf_id} in time.")


def _localise_figures(markdown: str, out_dir: Path) -> str:
    """Download remote figures into ``out_dir/media`` and repoint the markdown at them."""
    markdown = markdown.replace("![]", "![pictureTag]")

    for idx, url in enumerate(dict.fromkeys(_REMOTE_IMAGE.findall(markdown))):
        basename = os.path.basename(url).split("?")[0] or f"figure_{idx}.png"
        local_name = f"{idx}_{basename}"

        image = requests.get(url)
        if image.status_code != 200:
            continue

        (out_dir / "media" / local_name).write_bytes(image.content)
        markdown = markdown.replace(url, f"./media/{local_name}")

    return markdown
