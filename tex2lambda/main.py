"""The main input for tex2lambda, defining both the CLT and main library function."""

import importlib
import pkgutil
from typing import Optional

import panflute as pf
import rich_click as click

import tex2lambda.filters
from tex2lambda.api.module import Module
from tex2lambda.json_convert import json_convert


def runner(
    question_file: str,
    chosen_filter: str,
    output_dir: Optional[str] = None,
    answer_file: Optional[str] = None,
) -> Module:
    r"""Takes in a TeX file for a given subject and outputs how it's broken down within Lambda Feedback.

    Args:
        question_file: The absolute path to a TeX question file.
        chosen_filter: The filter chosen to parse the TeX file.
        output_dir: An optional argument for where to output the Lambda Feedback compatible json/zip files.
        answer_file: The absolute path to a TeX answer file.

    Returns:
        A list of questions and how they would be broken down into different Lambda Feedback sections
        in a Python-readable format. If `output_dir` is specified, the corresponding json/zip files are
        produced.

    Examples:
        >>> import os
        >>> from tex2lambda.main import runner
        >>> # Retrieve an example TeX file and run the given filter.
        >>> runner(f"{os.path.dirname(tex2lambda.__file__)}/filters/PartsSepSol/example.tex", "PartsSepSol") # doctest: +ELLIPSIS
        Module(questions=[Question(title='', parts=[Part(text=..., worked_solution=''), ...], images=[], _main_text='This is a sample question\n\n'), ...])
        >>> runner(f"{os.path.dirname(tex2lambda.__file__)}/filters/PartsOneSol/example.tex", "PartsOneSol") # doctest: +ELLIPSIS
        Module(questions=[Question(title='', parts=[Part(text='This is part (a)\n\n', worked_solution=''), ...], images=[], _main_text='Here is some preliminary question information that might be useful.'), ...)
    """
    # The list of questions for Lambda Feedback as a Python API.
    module = Module()

    # Dynamically import the correct pandoc filter depending on the subject.
    filter_module = importlib.import_module(
        f"tex2lambda.filters.{chosen_filter}.filter"
    )

    with open(question_file, "r", encoding="utf-8") as file:
        text = file.read()

    # Parse the Pandoc AST using the relevant panflute filter.
    pf.run_filter(
        filter_module.pandoc_filter,
        doc=pf.convert_text(text, input_format="latex", standalone=True),
        module=module,
        tex_file=question_file,
        parsing_answers=False,
    )

    # If separate answer TeX file provided, parse that as well.
    if answer_file:
        with open(answer_file, "r", encoding="utf-8") as file:
            answer_text = file.read()

        pf.run_filter(
            filter_module.pandoc_filter,
            doc=pf.convert_text(answer_text, input_format="latex", standalone=True),
            module=module,
            tex_file=answer_file,
            parsing_answers=True,
        )

    # Read the Python API format and convert to JSON.
    if output_dir is not None:
        json_convert.main(module.questions, output_dir)

    return module


@click.command(
    epilog="See the docs at https://lambda-feedback.github.io/user-documentation/ for more details."
)
@click.argument(  # Use resolve_path to get absolute path
    "question_file", type=click.Path(exists=True, readable=True, resolve_path=True)
)
# Python files in the subjects directory
@click.argument(
    "chosen_filter",
    type=click.Choice(
        [
            i.name
            for i in pkgutil.iter_modules(tex2lambda.filters.__path__)
            if i.name[0] != "_"
        ],
        case_sensitive=False,
    ),
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
    help="File containing solutions for QUESTION_FILE.",
    type=click.Path(resolve_path=True, exists=True, dir_okay=False),
)
def cli(
    question_file: str, chosen_filter: str, output_dir: str, answer_file: Optional[str]
) -> None:
    """Takes in a QUESTION_FILE for a given SUBJECT and produces Lambda Feedback compatible json/zip files."""
    # main() is made separate from click() so that it can be easily imported as part of a library.
    runner(question_file, chosen_filter, output_dir, answer_file)


if __name__ == "__main__":
    cli()
