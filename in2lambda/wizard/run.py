"""Drive the wizard: unstructured document in, ``#``/``##`` markdown out.

The output is written for a human to review and tweak before running it through
``in2lambda convert ... Markdown``. Along the way the instructor confirms the
response area proposed for each part (unless ``--yes`` / ``--no-response-areas``
say otherwise).
"""

import sys
from pathlib import Path
from typing import Optional

import rich_click as click

from in2lambda.llm import get_client, resolve_model
from in2lambda.main import docx_to_md, file_type
from in2lambda.validation import check_markdown
from in2lambda.wizard.confirm import confirm_response_areas
from in2lambda.wizard.extract import extract_set, to_markdown
from in2lambda.wizard.mathpix import pdf_to_markdown


def _load_markdown(source: Path, media_dir: Path) -> str:
    """Return ``source`` as markdown/LaTeX text, running OCR for PDFs."""
    if source.suffix.lower() == ".pdf":
        return pdf_to_markdown(str(source), str(media_dir)).read_text(encoding="utf-8")
    if file_type(str(source)) == "docx":
        return docx_to_md(str(source))
    return source.read_text(encoding="utf-8")


def run_wizard(
    input_file: str,
    output_file: str,
    model: Optional[str] = None,
    *,
    response_areas: bool = True,
    assume_yes: bool = False,
) -> Path:
    """Convert ``input_file`` (PDF/docx/tex/md) to reviewable markdown at ``output_file``.

    Args:
        input_file: The unstructured source document.
        output_file: Where to write the ``#``/``##`` markdown.
        model: OpenRouter model slug; defaults to ``$IN2LAMBDA_MODEL`` or the
            built-in default.
        response_areas: Whether to include response areas at all. When ``False``
            every proposed response area is dropped.
        assume_yes: Keep every proposed response area without prompting.

    Returns:
        The path to the written markdown file.
    """
    source = Path(input_file)
    output = Path(output_file)
    output.parent.mkdir(parents=True, exist_ok=True)

    source_markdown = _load_markdown(source, output.parent)

    client = get_client()
    question_set = extract_set(source_markdown, client, resolve_model(model))

    interactive = response_areas and not assume_yes and sys.stdin.isatty()
    question_set = confirm_response_areas(
        question_set, accept_all=not interactive, enabled=response_areas
    )

    markdown = to_markdown(question_set)

    for problem in check_markdown(markdown):
        click.echo(f"Warning: {problem.value}")

    output.write_text(markdown, encoding="utf-8")
    return output
