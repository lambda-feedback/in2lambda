"""The main input for in2lambda, defining both the CLT and main library function."""

# This commented block makes it run the local files rather than the pip library (I think, I don't understand it. Kevin wrote it.)
#
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import getpass
import importlib
import shlex
from collections.abc import Iterator  # Rather than typing's, which beartype warns on.
from contextlib import contextmanager
from typing import Optional

import rich_click as click

import in2lambda.draft
import in2lambda.filters
import in2lambda.source
from in2lambda.api.set import Set

# All four are in other people's scripts as in2lambda.main names, whether or not they
# are used here: `_pandoc` and `file_type` were defined here before there was an
# in2lambda.source, and `ConversionToolsMissing` is what `runner` documents raising.
from in2lambda.source import (
    ConversionToolsMissing,
    SourceError,
    _pandoc,
    _require_conversion_tools,
    file_type,
)


@contextmanager
def _message_not_traceback() -> Iterator[None]:
    """Turns anything raised for a reader into what to do about it and a non-zero exit.

    Every command wraps whatever it calls in this: a missing pandoc, a draft from
    somewhere else, a source that has moved on are all things the person running it can
    act on, and none of them are worth a traceback.
    """
    try:
        yield
    except SourceError as error:
        raise click.ClickException(str(error)) from None


def docx_to_md(docx_file: str) -> str:
    """Converts .docx files to markdown.

    Args:
        docx_file: A file path with the file extension included.

    Returns:
        the contents of the .docx file in markdown formatting
    """
    return _pandoc(docx_file, "markdown").decode("utf-8")


def runner(
    question_file: str,
    chosen_filter: str,
    output_dir: Optional[str] = None,
    answer_file: Optional[str] = None,
) -> Set:
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

    Raises:
        ConversionToolsMissing: pandoc or panflute is not installed.

    Examples:
        >>> import os
        >>> from in2lambda.main import runner
        >>> # Retrieve an example TeX file and run the given filter.
        >>> runner(f"{os.path.dirname(in2lambda.__file__)}/filters/PartsSepSol/example.tex", "PartsSepSol") # doctest: +ELLIPSIS
        Set(_name='set', _description='', _finalAnswerVisibility='OPEN_WITH_WARNINGS', _workedSolutionVisibility='OPEN_WITH_WARNINGS', _structuredTutorialVisibility='OPEN', questions=[Question(title='', parts=[Part(text=..., worked_solution='', answer='', response_areas=[]), ...], images=[], main_text='This is a sample question\n\n'), ...])
        >>> runner(f"{os.path.dirname(in2lambda.__file__)}/filters/PartsOneSol/example.tex", "PartsOneSol") # doctest: +ELLIPSIS
        Set(_name='set', _description='', _finalAnswerVisibility='OPEN_WITH_WARNINGS', _workedSolutionVisibility='OPEN_WITH_WARNINGS', _structuredTutorialVisibility='OPEN', questions=[Question(title='', parts=[Part(text=..., worked_solution='', answer='', response_areas=[]), ...], images=[], main_text='Here is some preliminary question information that might be useful.'), ...])
    """
    _require_conversion_tools()
    import panflute as pf

    # The list of questions for Lambda Feedback as a Python API.
    set_obj = Set()

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
        set=set_obj,
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
            set=set_obj,
            tex_file=answer_file,
            parsing_answers=True,
        )

    # Report before writing anything: the problems are the set's whether or not it is
    # written out, and an author reading the command line should see them first.
    for problem in set_obj.problems():
        click.echo(f"Warning: {problem}")

    # Read the Python API format and convert to JSON.
    if output_dir is not None:
        set_obj.to_json(output_dir)

    return set_obj


class _Cli(click.RichGroup):
    """The in2lambda group, which says what to run when given the pre-2.0 command line."""

    def resolve_command(self, ctx, args):  # type: ignore[no-untyped-def]
        """Fail with the new command line rather than click's handling of an unknown name.

        Click resolves a first argument starting with ``/`` or ``.`` by printing the
        group's help and exiting successfully, so `in2lambda /path/to/questions.tex
        PartsSepSol` would look like it had worked while converting nothing.
        """
        # Shell completion resolves partial command lines, and must not raise.
        if not ctx.resilient_parsing and self.get_command(ctx, args[0]) is None:
            raise click.UsageError(
                f"in2lambda no longer takes a file directly. Run: in2lambda convert {shlex.join(args)}"
            )
        return super().resolve_command(ctx, args)


@click.group(
    cls=_Cli,
    no_args_is_help=True,
    epilog="See the docs at https://lambda-feedback.github.io/in2lambda/ for more details.",
)
def cli() -> None:
    """Prepares content for import into Lambda Feedback."""


@cli.command()
@click.argument(  # Use resolve_path to get absolute path
    "question_file", type=click.Path(exists=True, readable=True, resolve_path=True)
)
# Python files in the subjects directory
@click.argument(
    "chosen_filter",
    type=click.Choice(in2lambda.filters.builtin_filters(), case_sensitive=False),
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
def convert(
    question_file: str, chosen_filter: str, output_dir: str, answer_file: Optional[str]
) -> None:
    """Takes in a QUESTION_FILE for a given SUBJECT and produces Lambda Feedback compatible json/zip files."""
    # main() is made separate from click() so that it can be easily imported as part of a library.
    with _message_not_traceback():
        runner(question_file, chosen_filter, output_dir, answer_file)


@cli.group("source")
def source_group() -> None:
    """Freezes a source document, so its text can be quoted by line range."""


@source_group.command("add")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option(
    "--start-over",
    is_flag=True,
    help="Freeze FILE again, discarding the draft already there.",
)
def source_add(file: str, start_over: bool) -> None:
    """Converts FILE to markdown and records its blocks in draft.json beside it."""
    with _message_not_traceback():
        draft = in2lambda.source.add(file, start_over)
    click.echo(f"Wrote {draft}")


@source_group.command("show")
def source_show() -> None:
    """Prints the frozen markdown of the draft in this directory, numbered."""
    with _message_not_traceback():
        click.echo(in2lambda.source.show())


@cli.group("draft")
def draft_group() -> None:
    """Builds up the draft in this directory, recording every command in it."""


@draft_group.group("mark")
def draft_mark() -> None:
    """Says what to make of a block of the frozen source."""


@draft_mark.command("ignore")
@click.argument("block")
@click.option(
    "--by",
    default=getpass.getuser,
    help="Who to record the command as having been run by.  [default: your username]",
)
def draft_mark_ignore(block: str, by: str) -> None:
    """Marks BLOCK as nothing to take a question from."""
    with _message_not_traceback():
        in2lambda.draft.execute(
            {"command": "mark ignore", "args": {"block": block}, "by": by}
        )


@draft_group.command("replay")
def draft_replay() -> None:
    """Rebuilds the draft in this directory from its log and checks it is the same."""
    with _message_not_traceback():
        in2lambda.draft.replay()
    click.echo("Replays as it stands.")


if __name__ == "__main__":
    cli()
