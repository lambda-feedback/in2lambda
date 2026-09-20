"""The main input for in2lambda, defining both the CLT and main library function."""

# This commented block makes it run the local files rather than the pip library (I think, I don't understand it. Kevin wrote it.)
#
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import getpass
import importlib
import shlex
import warnings
from collections.abc import (  # Rather than typing's, which beartype warns on.
    Callable,
    Iterator,
)
from contextlib import contextmanager
from typing import Any, Optional

import rich_click as click

import in2lambda.draft
import in2lambda.draft.export
import in2lambda.draft.report
import in2lambda.filters
import in2lambda.source
from in2lambda.api.set import Set

# All four are in other people's scripts as in2lambda.main names, whether or not they
# are used here: `_pandoc` and `file_type` were defined here before there was an
# in2lambda.source, and `ConversionToolsMissing` is what `runner` documents raising.
from in2lambda.source import (  # noqa: F401  # Re-exported, so not unused.
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


@contextmanager
def _warnings_said() -> Iterator[None]:
    """Echoes whatever is warned inside it as a line, as `runner` says its problems.

    What `build` and `render` warn about is something they wrote out anyway - a question
    nothing answers, a question xelatex gave up on - so it belongs beside what they
    wrote, and is said even where the command goes on to refuse for another reason.
    """
    with warnings.catch_warnings(record=True) as said:
        warnings.simplefilter("always")
        try:
            yield
        finally:
            for warning in said:
                click.echo(f"Warning: {warning.message}")


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
    # written out, and an author reading the command line should see them first. A check
    # that could not be run at all - the maths, with no Node.js to render it - warns
    # instead, and is caught here so that it reads as a line rather than a traceback.
    with warnings.catch_warnings(record=True) as not_checked:
        warnings.simplefilter("always")
        problems = set_obj.problems()
    for problem in problems:
        click.echo(f"Warning: {problem}")
    for warning in not_checked:
        click.echo(f"Warning: {warning.message}")

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
    """Freezes the source documents of a draft, so their text can be quoted by line range."""


@source_group.command("add")
@click.argument(
    "files",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "--start-over",
    is_flag=True,
    help="Freeze FILES again, discarding the draft already there.",
)
def source_add(files: tuple[str, ...], start_over: bool) -> None:
    """Converts each FILE to markdown and records its blocks in draft.json beside them.

    A sheet written as two documents - the questions in one file and the solutions in
    another - is frozen as both, in that order: in2lambda source add questions.docx
    solutions.docx. A file can be added to the draft later, as the next source. The
    first source's blocks and lines are named b3 and s10:14; every source after it
    carries its number - 2/b3, 2/s10:14.
    """
    with _message_not_traceback():
        draft = in2lambda.source.add(list(files), start_over)
    click.echo(f"Wrote {draft}")


@source_group.command("show")
def source_show() -> None:
    """Prints the frozen markdown of the draft in this directory, numbered."""
    with _message_not_traceback():
        click.echo(in2lambda.source.show())


@cli.group("draft")
def draft_group() -> None:
    """Builds up the draft in this directory, recording every command in it."""


_by = click.option(
    "--by",
    default=getpass.getuser,
    help="Who to record the command as having been run by.  [default: your username]",
)
"""Who ran a draft command, which every one of them records."""


def _text_or_literal(command: Callable[..., None]) -> Callable[..., None]:
    """The two ways to fill a field: quoted from the frozen source, or typed out."""
    for option in (
        click.option(
            "--literal",
            help="The text itself, where the source does not say it in a form the "
            "field can take. Marks the field as edited.",
        ),
        click.option(
            "--text",
            help="Where in a frozen source the text is: a block id such as b3, or "
            "lines such as s10:14, with the source's number in front - 2/b3, 2/s10:14 "
            "- for any but the first. Run in2lambda source show to see both.",
        ),
    ):
        command = option(command)
    return command


def _run(command: str, args: dict[str, Any], by: str) -> None:
    """Runs one draft command against the draft here and says what it wrote.

    Arguments nobody gave are left out rather than recorded as nulls: the log is what a
    replay runs, and an option that was not passed is not an argument of the command.
    """
    with _message_not_traceback():
        written = in2lambda.draft.execute(
            {
                "command": command,
                "args": {
                    name: given for name, given in args.items() if given is not None
                },
                "by": by,
            }
        )
    click.echo(f"Wrote {written}.")


@draft_group.group("mark")
def draft_mark() -> None:
    """Says what to make of a block of the frozen source."""


@draft_mark.command("ignore")
@click.argument("block")
@_by
def draft_mark_ignore(block: str, by: str) -> None:
    """Marks BLOCK as nothing to take a question from."""
    _run("mark ignore", {"block": block}, by)


@draft_group.group("question")
def draft_question() -> None:
    """Adds a question to the draft, or says where its solution is written."""


@draft_question.command("add")
@_text_or_literal
@_by
def draft_question_add(text: Optional[str], literal: Optional[str], by: str) -> None:
    """Adds a question, numbered after the ones already there."""
    _run("question add", {"text": text, "literal": literal}, by)


@draft_question.command("solution")
@click.argument("question")
@_text_or_literal
@_by
def draft_question_solution(
    question: str, text: Optional[str], literal: Optional[str], by: str
) -> None:
    """Gives QUESTION the worked solution written at --text or --literal."""
    _run(
        "question solution",
        {"question": question, "text": text, "literal": literal},
        by,
    )


@draft_group.group("part")
def draft_part() -> None:
    """Adds a part to a question of the draft."""


@draft_part.command("add")
@click.argument("question")
@_text_or_literal
@_by
def draft_part_add(
    question: str, text: Optional[str], literal: Optional[str], by: str
) -> None:
    """Adds a part of QUESTION, numbered after the parts it already has."""
    _run("part add", {"question": question, "text": text, "literal": literal}, by)


@draft_group.group("split")
def draft_split() -> None:
    """Cuts up a block of the frozen source that is really two things."""


@draft_split.command("block")
@click.argument("block")
@click.argument("at", type=int)
@_by
def draft_split_block(block: str, at: int, by: str) -> None:
    """Splits BLOCK in two, the second half starting at line AT."""
    _run("split block", {"block": block, "at": at}, by)


@draft_group.group("field")
def draft_field() -> None:
    """Changes the wording of a field the draft has written already."""


@draft_field.command("replace")
@click.argument("field")
@click.argument("old")
@click.argument("new")
@click.option(
    "--regex",
    is_flag=True,
    help="Read OLD as a regular expression, and NEW as what to replace it with.",
)
@_by
def draft_field_replace(field: str, old: str, new: str, regex: bool, by: str) -> None:
    """Replaces OLD with NEW in FIELD, which OLD has to occur exactly once in."""
    _run(
        "field replace",
        {"field": field, "old": old, "new": new, "regex": True if regex else None},
        by,
    )


@draft_group.command("replay")
def draft_replay() -> None:
    """Rebuilds the draft in this directory from its log and checks it is the same."""
    with _message_not_traceback():
        in2lambda.draft.replay()
    click.echo("Replays as it stands.")


@cli.group("spec")
def spec_group() -> None:
    """Runs a YAML spec of selectors over the frozen source in this directory."""


@spec_group.command("run")
@click.argument("spec", type=click.Path(exists=True, dir_okay=False))
@_by
def spec_run(spec: str, by: str) -> None:
    """Fills the draft's fields in from SPEC, and says which blocks it left out."""
    with _message_not_traceback():
        report = in2lambda.draft.execute(in2lambda.draft.spec_command(spec, by))
    click.echo(report)


@cli.command("validate")
def validate() -> None:
    """Checks the draft in this directory over and writes the report into it.

    Reports source blocks in no field and not marked ignore, two fields taken from the
    same lines, gaps in the numbering of the questions or their parts, and fields holding
    nothing. The set the draft describes is checked over as well - maths delimiters, what
    KaTeX will not render, images the export would not carry, and the compile Lambda
    Feedback's PDF generator does where pandoc and xelatex are installed - each against
    the field it is written in. All of those in2lambda build refuses; a question or part
    nothing answers is reported as a warning, which it builds over. Finding something is
    not a failure: the report is written into draft.json either way, and replaced by the
    next one.
    """
    with _message_not_traceback():
        report = in2lambda.draft.report.validate()
    for finding in report:
        # Marked as such, since the two are acted on differently and the report is often
        # read off the terminal rather than out of the draft.
        if finding["level"] == in2lambda.draft.report.WARNING:
            click.echo(f"Warning: {finding['message']}")
        else:
            click.echo(finding["message"])
    if not report:
        click.echo("Nothing to report.")


_out = click.option(
    "--out",
    "-o",
    "output_dir",
    default="./out",
    show_default=True,
    help="Directory to write the files to.",
    type=click.Path(resolve_path=True),
)
"""Where what a command makes is written, as `convert` has always taken it."""


@cli.command("build")
@_out
def build(output_dir: str) -> None:
    """Writes the draft in this directory out as a Lambda Feedback set.

    Refused unless in2lambda validate has been run since the draft last changed and
    found no error, so that what is uploaded is what the checks have been over. What it
    found at level warning - a question or part with no solution written for it - is
    said, and the set written all the same.
    """
    with _message_not_traceback(), _warnings_said():
        written = in2lambda.draft.export.build(output_dir=output_dir)
    click.echo(f"Wrote {written}")


@cli.command("render")
@_out
def render(output_dir: str) -> None:
    """Writes each question of the draft in this directory as a PDF, for review.

    The questions are compiled as Lambda Feedback's PDF generator compiles them, which
    needs pandoc and xelatex. What the checks have to say about the draft is not asked:
    a draft is rendered to look at, including one there is something to fix in.
    """
    # A question xelatex complains about is still written out, and what it refused is a
    # line to read rather than a traceback.
    with _message_not_traceback(), _warnings_said():
        written = in2lambda.draft.export.render(output_dir=output_dir)
    for pdf in written:
        click.echo(f"Wrote {pdf}")


if __name__ == "__main__":
    cli()
