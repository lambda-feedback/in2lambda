"""The main input for in2lambda, defining both the CLT and main library function."""

# This commented block makes it run the local files rather than the pip library (I think, I don't understand it. Kevin wrote it.)
#
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib
import pkgutil
import subprocess
from typing import Optional

import panflute as pf
import rich_click as click

import in2lambda.filters
from in2lambda.api.module import Module

def docx_to_md(docx_file: str) -> str:
    """Converts .docx files to markdown
    Args:
        docx_file: A file path with the file extension included
    Returns:
        the contents of the .docx file in markdown formatting 
    """
    md_output = subprocess.check_output(["pandoc", docx_file, "-t", "markdown"])
    return md_output.decode("utf-8")


def file_type(file: str) -> str:
    """Determines which pandoc file format to use for a given file.

    See https://github.com/jgm/pandoc/blob/bad922a69236e22b20d51c4ec0b90c5a6c038433/src/Text/Pandoc/Format.hs#L171
    (or any newer commit) for pandoc's supported file extensions.

    Args:
        file: A file path with the file extension included.

    Returns:
        An option in `pandoc --list-input-formats` that matches the given file type

    Examples:
        >>> from in2lambda.main import file_type
        >>> file_type("example.tex")
        'latex'
        >>> file_type("/some/random/path/demo.md")
        'markdown'
        >>> file_type("no_extension")
        Traceback (most recent call last):
        RuntimeError: Unsupported file extension: .no_extension
        >>> file_type("demo.unknown_extension")
        Traceback (most recent call last):
        RuntimeError: Unsupported file extension: .unknown_extension
    """
    match (extension := file.split(".")[-1].lower()):
        case "tex" | "latex" | "ltx":
            return "latex"
        case (
            "md"
            | "rmd"
            | "markdown"
            | "mdown"
            | "mdwn"
            | "mkd"
            | "mkdn"
            | "text"
            | "txt"
        ):
            return "markdown"
        case "docx":
            return "docx"  # Pandoc doesn't seem to support .doc, and panflute doesn't like .docx.
    raise RuntimeError(f"Unsupported file extension: .{extension}")


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
        >>> from in2lambda.main import runner
        >>> # Retrieve an example TeX file and run the given filter.
        >>> runner(f"{os.path.dirname(in2lambda.__file__)}/filters/PartsSepSol/example.tex", "PartsSepSol") # doctest: +ELLIPSIS
        Module(questions=[Question(title='', parts=[Part(text=..., worked_solution=''), ...], images=[], main_text='This is a sample question\n\n'), ...])
        >>> runner(f"{os.path.dirname(in2lambda.__file__)}/filters/PartsOneSol/example.tex", "PartsOneSol") # doctest: +ELLIPSIS
        Module(questions=[Question(title='', parts=[Part(text='This is part (a)\n\n', worked_solution=''), ...], images=[], main_text='Here is some preliminary question information that might be useful.'), ...)
    """
    # The list of questions for Lambda Feedback as a Python API.
    module = Module()

    # Dynamically import the correct pandoc filter depending on the subject.
    filter_module = importlib.import_module(f"in2lambda.filters.{chosen_filter}.filter")

    if file_type(question_file) == "docx":
        # Convert .docx to md using Pandoc and proceed
        text = docx_to_md(question_file)
        input_format = "markdown"
    else:
        with open(question_file, "r", encoding="utf-8") as file:
            text = file.read()

        input_format = file_type(question_file)

    # Parse the Pandoc AST using the relevant panflute filter.
    pf.run_filter(
        filter_module.pandoc_filter,
        doc=pf.convert_text(text, input_format=input_format, standalone=True),
        module=module,
        tex_file=question_file,
        parsing_answers=False,
    )

    # If separate answer TeX file provided, parse that as well.
    if answer_file:

        if file_type(answer_file) == "docx":

            answer_text = docx_to_md(answer_file)
            answer_format = "markdown"
        else:
            with open(answer_file, "r", encoding="utf-8") as file:
                answer_text = file.read()
            answer_format = file_type(answer_file)

        pf.run_filter(
            filter_module.pandoc_filter,
            doc=pf.convert_text(
                answer_text, input_format=answer_format, standalone=True
            ),
            module=module,
            tex_file=answer_file,
            parsing_answers=True,
        )

    # Read the Python API format and convert to JSON.
    if output_dir is not None:
        module.to_json(output_dir)

    return module


@click.command(
    no_args_is_help=True,
    epilog="See the docs at https://lambda-feedback.github.io/in2lambda/ for more details.",
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
            for i in pkgutil.iter_modules(in2lambda.filters.__path__)
            if i.name != "markdown"
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
