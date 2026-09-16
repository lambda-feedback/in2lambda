"""Convert a PDF into markdown with the Mathpix OCR API.

Needs ``MATHPIX_APP_ID`` and ``MATHPIX_API_KEY`` in the environment (a ``.env``
file is honoured by the wizard). Figures referenced by the returned markdown are
downloaded next to it so the ``Markdown`` filter can pick them up.

The PDF is uploaded to Mathpix, a third-party OCR service, for processing.
Instructors converting student work should be told their PDFs leave the
local machine. Mathpix also offers an opt-out from using submitted data to
improve its models; see https://mathpix.com/privacy for how to enable it.
"""

import os
import re
import time
import warnings
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
    timeout: float = 30.0,
) -> str:
    """Convert ``pdf_path`` to markdown, downloading its figures under ``out_dir``.

    Args:
        pdf_path: Path to the source PDF.
        out_dir: Directory to write a ``media/`` folder of figures into.
        poll_interval: Seconds to wait between Mathpix "is it ready yet" polls.
        max_polls: How many times to poll before giving up.
        timeout: Seconds to wait for each individual HTTP request.

    Returns:
        The converted markdown, with figures saved in ``<out_dir>/media/`` and
        referenced from the markdown as ``./media/<name>``. The caller is
        responsible for writing the markdown out wherever it belongs.

    Raises:
        RuntimeError: if credentials are missing, Mathpix rejects the PDF or
            fails to convert it, or the conversion does not finish in time.
    """
    headers = _headers()
    out = Path(out_dir)
    (out / "media").mkdir(parents=True, exist_ok=True)

    with open(pdf_path, "rb") as pdf:
        response = requests.post(
            MATHPIX_PDF_ENDPOINT,
            headers=headers,
            files={"file": pdf},
            timeout=timeout,
        )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Mathpix rejected the PDF: {data['error']}")
    pdf_id = data["pdf_id"]

    markdown = _poll_for_markdown(pdf_id, headers, poll_interval, max_polls, timeout)
    return _localise_figures(markdown, out, timeout)


def _poll_for_markdown(
    pdf_id: str,
    headers: dict,
    poll_interval: float,
    max_polls: int,
    timeout: float,
) -> str:
    """Poll Mathpix until ``pdf_id`` finishes converting, then return its markdown."""
    status_url = f"{MATHPIX_PDF_ENDPOINT}/{pdf_id}"
    for _ in range(max_polls):
        response = requests.get(status_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        if status == "completed":
            break
        if status == "error":
            raise RuntimeError(
                f"Mathpix failed to convert {pdf_id}: {data.get('error', 'unknown error')}"
            )
        time.sleep(poll_interval)
    else:
        raise RuntimeError(f"Mathpix did not finish converting {pdf_id} in time.")

    md_response = requests.get(
        f"{MATHPIX_PDF_ENDPOINT}/{pdf_id}.md", headers=headers, timeout=timeout
    )
    md_response.raise_for_status()
    return md_response.text


def _localise_figures(markdown: str, out_dir: Path, timeout: float) -> str:
    """Download remote figures into ``out_dir/media`` and repoint the markdown at them."""
    markdown = markdown.replace("![]", "![pictureTag]")

    for idx, url in enumerate(dict.fromkeys(_REMOTE_IMAGE.findall(markdown))):
        basename = os.path.basename(url).split("?")[0] or f"figure_{idx}.png"
        local_name = f"{idx}_{basename}"

        image = requests.get(url, timeout=timeout)
        if image.status_code != 200:
            warnings.warn(
                f"Mathpix figure download failed for {url} "
                f"(status {image.status_code}); markdown will reference a "
                f"missing file: ./media/{local_name}"
            )
            continue

        (out_dir / "media" / local_name).write_bytes(image.content)
        markdown = markdown.replace(url, f"./media/{local_name}")

    return markdown
