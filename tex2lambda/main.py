"""The main input for tex2lambda, defining both the CLT and main library function."""

import importlib
from typing import Optional

import panflute as pf
import rich_click as click

from tex2lambda import question
from tex2lambda.json_convert import json_convert


def runner(
    tex_file: str,
    subject: str,
    output_dir: Optional[str] = None,
    answer_file: Optional[str] = None,
) -> question.Questions:
    """Takes in a TeX file for a given subject and outputs how it's broken down within Lambda Feedback.

    Args:
        tex_file: The absolute path to a TeX file.
        subject: The subject which the TeX file contains questions for.
        output_dir: An optional argument for where to output the Lambda Feedback compatible json/zip files.

    Returns:
        A list of questions and how they would be broken down into different Lambda Feedback sections
        in a Python-readable format. If `output_dir` is specified, the corresponding json/zip files are
        produced.
    """
    # The list of questions for Lambda Feedback as a Python API.
    # See `tex2lambda.question` for the full structure of Questions()
    questions = question.Questions()

    # Dynamically import the correct pandoc filter depending on the subject.
    subject_module = importlib.import_module(f"tex2lambda.subjects.{subject.lower()}")

    with open(tex_file, "r", encoding="utf-8") as file:
        text = file.read()

    # Parse the Pandoc AST using the relevant panflute filter.
    pf.run_filter(
        subject_module.pandoc_filter,
        doc=pf.convert_text(text, input_format="latex", standalone=True),
        questions=questions,
        tex_file=tex_file,
        parsing_answers=False,
    )

    # If separate answer TeX file provided, parse that as well.
    if answer_file:
        with open(answer_file, "r", encoding="utf-8") as file:
            answer_text = file.read()

        pf.run_filter(
            subject_module.pandoc_filter,
            doc=pf.convert_text(answer_text, input_format="latex", standalone=True),
            questions=questions,
            tex_file=tex_file,
            parsing_answers=True,
        )

    # Read the Python API format and convert to JSON.
    if output_dir is not None:
        json_convert.main(questions.questions, output_dir)

    return questions


@click.command(
    epilog="See the docs at https://lambda-feedback.github.io/user-documentation/ for more details."
)
@click.argument(  # Use resolve_path to get absolute path
    "tex_file", type=click.Path(exists=True, readable=True, resolve_path=True)
)
# TODO: Automate argument generation
@click.argument(
    "subject",
    type=click.Choice(["Materials", "Fourier"], case_sensitive=False),
)
@click.option(
    "--out",
    "-o",
    "output_dir",
    default="./out",
    show_default=True,
    help="Directory to output json/zip files to.",
    type=click.Path(resolve_path=True),
)
@click.option(
    "--answers",
    "-a",
    "answer_file",
    default=None,
    help="File containing solutions for TEX_FILE.",
    type=click.Path(resolve_path=True, exists=True, dir_okay=False),
)
def cli(
    tex_file: str, subject: str, output_dir: str, answer_file: Optional[str]
) -> None:
    """Takes in a TEX_FILE for a given SUBJECT and produces Lambda Feedback compatible json/zip files."""
    # main() is made separate from click() so that it can be easily imported as part of a library.
    runner(tex_file, subject, output_dir, answer_file)


if __name__ == "__main__":
    cli()
