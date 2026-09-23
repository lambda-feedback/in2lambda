"""The in2lambda command line, and the library function behind `in2lambda convert`."""

import getpass
import importlib
import os
import shlex
import warnings
import zipfile
from collections.abc import Callable  # Rather than typing's, which beartype warns on.
from contextlib import contextmanager
from typing import Any, Optional

import rich_click as click

import in2lambda.compare
import in2lambda.draft
import in2lambda.draft.export
import in2lambda.draft.report
import in2lambda.filters
import in2lambda.source
from in2lambda.api.set import Set

# Other people's scripts import all four as in2lambda.main names: `_pandoc` and
# `file_type` were defined here before in2lambda.source existed, and `runner` documents
# raising `ConversionToolsMissing`.
from in2lambda.source import (  # noqa: F401  # Re-exported, so not unused.
    ConversionToolsMissing,
    SourceError,
    _pandoc,
    _require_conversion_tools,
    file_type,
)


@contextmanager
def _message_not_traceback():  # No annotation: beartype 0.22 on 3.10 checks the
    # decorated object, a _GeneratorContextManager, against a generator hint.
    """Turns a `SourceError` into a message and a non-zero exit.

    Every command wraps its call in this. A missing pandoc, a draft another tool wrote
    and a source that has changed are faults the person running the command can act on,
    and a traceback tells them less than the message does.
    """
    try:
        yield
    except SourceError as error:
        raise click.ClickException(str(error)) from None


@contextmanager
def _warnings_said():  # Unannotated for the same reason as _message_not_traceback.
    """Echoes each warning raised inside it as a line, as `runner` prints its problems.

    `build` and `render` warn about a question they wrote out all the same - a question
    nothing answers, a question xelatex gave up on - so each warning is printed beside
    the paths the command printed, and is printed where the command then refuses for
    another reason.
    """
    with warnings.catch_warnings(record=True) as said:
        warnings.simplefilter("always")
        try:
            yield
        finally:
            for warning in said:
                click.echo(f"Warning: {warning.message}")


def docx_to_md(docx_file: str) -> str:
    """Converts a .docx file to markdown.

    Args:
        docx_file: A file path, including the file extension.

    Returns:
        The contents of the .docx file as markdown.
    """
    return _pandoc(docx_file, "markdown").decode("utf-8")


def runner(
    question_file: str,
    chosen_filter: str,
    output_dir: Optional[str] = None,
    answer_file: Optional[str] = None,
) -> Set:
    r"""Converts a question document into the set Lambda Feedback imports.

    Args:
        question_file: The absolute path to a question file.
        chosen_filter: The filter that parses the document.
        output_dir: Where to write the JSON and zip files. None writes no files.
        answer_file: The absolute path to a file of answers.

    Returns:
        The set the document describes, as questions holding parts. Where `output_dir` is
        given, `runner` also writes the JSON and zip files.

    Raises:
        ConversionToolsMissing: pandoc or panflute is not installed.

    Examples:
        >>> import os
        >>> from in2lambda.main import runner
        >>> # Retrieve an example TeX file and run the given filter.
        >>> runner(f"{os.path.dirname(in2lambda.__file__)}/filters/PartsSepSol/example.tex", "PartsSepSol") # doctest: +ELLIPSIS
        Set(_name='set', _description='', _finalAnswerVisibility='OPEN_WITH_WARNINGS', _workedSolutionVisibility='OPEN_WITH_WARNINGS', _structuredTutorialVisibility='OPEN', questions=[Question(title='', parts=[Part(text=..., worked_solution='', answer='', response_areas=[]), ...], images=[], main_text='This is a sample question\n\n'), ...])
        >>> runner(f"{os.path.dirname(in2lambda.__file__)}/filters/PartsOneSol/example.tex", "PartsOneSol") # doctest: +ELLIPSIS
        Set(_name='set', _description='', _finalAnswerVisibility='OPEN_WITH_WARNINGS', _workedSolutionVisibility='OPEN_WITH_WARNINGS', _structuredTutorialVisibility='OPEN', questions=[Question(title='', parts=[Part(text=..., worked_solution='This is the final answer...', answer='', response_areas=[]), ...], images=[...], main_text='Here is some preliminary question information that might be useful.'), ...])
    """
    _require_conversion_tools()
    import panflute as pf

    set_obj = Set()

    # The filter is named on the command line, so it is imported by name.
    filter_module = importlib.import_module(f"in2lambda.filters.{chosen_filter}.filter")

    if file_type(question_file) == "docx":
        text = docx_to_md(question_file)
        input_format = "markdown"
    else:
        with open(question_file, "r", encoding="utf-8") as file:
            text = file.read()

        input_format = file_type(question_file)

    pf.run_filter(
        filter_module.pandoc_filter,
        doc=pf.convert_text(text, input_format=input_format, standalone=True),
        set=set_obj,
        tex_file=question_file,
        parsing_answers=False,
    )

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

    # Reported before anything is written: the problems belong to the set whether or not
    # in2lambda writes it out, and an author reads them first. A check that could not run
    # at all - the maths, with no Node.js to render it - warns instead, and is caught
    # here so that it prints as a line and not as a traceback.
    with warnings.catch_warnings(record=True) as not_checked:
        warnings.simplefilter("always")
        problems = set_obj.problems()
    for problem in problems:
        click.echo(f"Warning: {problem}")
    for warning in not_checked:
        click.echo(f"Warning: {warning.message}")

    if output_dir is not None:
        set_obj.to_json(output_dir)

    return set_obj


class _Cli(click.RichGroup):
    """The in2lambda group, which runs `convert` for a first argument that is a file."""

    def resolve_command(self, ctx, args):  # type: ignore[no-untyped-def]
        """Runs `convert` for a file, and refuses a first argument that is neither.

        A first argument naming a file runs `in2lambda convert` on that file, and one
        line on stderr names the `in2lambda convert` command to run instead, so a script
        written before that command existed keeps working. A first argument that names
        neither a command nor a file is refused, and the message names the `in2lambda
        convert` command. Click prints the group's help and exits 0 for a first argument
        starting with ``/`` or ``.``, so `in2lambda /path/to/questions.tex PartsSepSol`
        would convert nothing and report no error.
        """
        # Shell completion resolves partial command lines, and must not raise.
        if not ctx.resilient_parsing and self.get_command(ctx, args[0]) is None:
            if os.path.isfile(args[0]):
                click.echo(
                    f"in2lambda FILE FILTER is the old form. Run: in2lambda convert {shlex.join(args)}",
                    err=True,
                )
                return super().resolve_command(ctx, ["convert", *args])
            raise click.UsageError(
                f"{args[0]} is not an in2lambda command, and no file of that name exists. "
                f"To convert a file, run: in2lambda convert {shlex.join(args)}"
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
@click.argument(
    "question_file", type=click.Path(exists=True, readable=True, resolve_path=True)
)
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
    help="Directory to write the JSON and zip files to.",
    type=click.Path(resolve_path=True),
)
@click.option(
    "--answers",
    "-a",
    "answer_file",
    default=None,
    help="File holding the solutions to QUESTION_FILE.",
    type=click.Path(resolve_path=True, exists=True, dir_okay=False),
)
def convert(
    question_file: str, chosen_filter: str, output_dir: str, answer_file: Optional[str]
) -> None:
    """Converts QUESTION_FILE with CHOSEN_FILTER into Lambda Feedback JSON and a zip."""
    # `runner` is separate from this command so that a script can import it.
    with _message_not_traceback():
        runner(question_file, chosen_filter, output_dir, answer_file)


@cli.group("source")
def source_group() -> None:
    """Freezes the source documents of a draft, so that their text can be quoted."""


_draft = click.option(
    "--draft",
    type=click.Path(exists=True, dir_okay=False),
    help="The draft to work on, as FILE.draft.json or the source it was frozen from. "
    " [default: the one draft in this directory]",
)
"""Which draft a command works on, because a folder of sheets holds a draft per sheet."""


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
@click.option(
    "--draft",
    type=click.Path(exists=True, dir_okay=False),
    help="The draft to freeze FILES into, as FILE.draft.json or a source already in "
    "it.  [default: the draft named after the first FILE]",
)
def source_add(files: tuple[str, ...], start_over: bool, draft: Optional[str]) -> None:
    """Converts each FILE to markdown and records its blocks in a draft beside them.

    The draft is named after the first file - questions.draft.json - unless --draft names
    the draft to freeze into. A sheet written as two documents, the questions in one file
    and the solutions in another, is frozen as both, in that order: in2lambda source add
    questions.docx solutions.docx. Naming an existing draft with --draft adds a file to
    that draft as its next source. The first source's blocks and lines are named b3 and
    s10:14, and every source after it carries its number: 2/b3, 2/s10:14.
    """
    with _message_not_traceback():
        written = in2lambda.source.add(list(files), start_over, draft)
    click.echo(f"Wrote {written}")


@source_group.command("show")
@_draft
def source_show(draft: Optional[str]) -> None:
    """Prints the frozen markdown of a draft, numbered."""
    with _message_not_traceback():
        click.echo(in2lambda.source.show(in2lambda.source.find(draft)))


@cli.group("draft")
def draft_group() -> None:
    """Builds a draft up, recording every command in the draft."""


_by = click.option(
    "--by",
    default=getpass.getuser,
    help="Who to record the command as having been run by.  [default: your username]",
)
"""Who ran a draft command, which every draft command records."""


_WHERE = (
    "Where the text is in a frozen source: a block id such as b3, or lines such as "
    "s10:14, with the source's number in front - 2/b3, 2/s10:14 - for any source "
    "after the first. Run in2lambda source show to see both."
)
"""The help for --text, which every command taking --text shares."""


def _text_or_literal(command: Callable[..., None]) -> Callable[..., None]:
    """The two ways to fill a field: quoted from the frozen source, or typed out."""
    for option in (
        click.option(
            "--literal",
            help="The text itself, for wording the source does not hold in a form the "
            "field takes. Marks the field as edited.",
        ),
        click.option("--text", help=_WHERE),
    ):
        command = option(command)
    return command


def _run(command: str, args: dict[str, Any], by: str, draft: Optional[str]) -> None:
    """Runs one draft command against the draft named, and prints the field it wrote.

    An argument the reader did not give is left out of the log, and is not recorded as
    null: a replay runs the log, and an option nobody passed is not an argument of the
    command.
    """
    with _message_not_traceback():
        written = in2lambda.draft.execute(
            {
                "command": command,
                "args": {
                    name: given for name, given in args.items() if given is not None
                },
                "by": by,
            },
            in2lambda.source.find(draft),
        )
    click.echo(f"Wrote {written}.")


@draft_group.group("mark")
def draft_mark() -> None:
    """Marks a block of the frozen source."""


@draft_mark.command("ignore")
@click.argument("block")
@_by
@_draft
def draft_mark_ignore(block: str, by: str, draft: Optional[str]) -> None:
    """Marks BLOCK as holding no question, part or solution."""
    _run("mark ignore", {"block": block}, by, draft)


@draft_group.group("question")
def draft_question() -> None:
    """Adds a question to the draft, or names where its solution is written."""


@draft_question.command("add")
@_text_or_literal
@_by
@_draft
def draft_question_add(
    text: Optional[str], literal: Optional[str], by: str, draft: Optional[str]
) -> None:
    """Adds a question, numbered after the questions already written."""
    _run("question add", {"text": text, "literal": literal}, by, draft)


@draft_question.command("solution")
@click.argument("question")
@_text_or_literal
@_by
@_draft
def draft_question_solution(
    question: str,
    text: Optional[str],
    literal: Optional[str],
    by: str,
    draft: Optional[str],
) -> None:
    """Gives QUESTION the worked solution written at --text or --literal."""
    _run(
        "question solution",
        {"question": question, "text": text, "literal": literal},
        by,
        draft,
    )


@draft_group.group("part")
def draft_part() -> None:
    """Adds a part to a question of the draft, or says where its solution is written."""


@draft_part.command("add")
@click.argument("question")
@_text_or_literal
@_by
@_draft
def draft_part_add(
    question: str,
    text: Optional[str],
    literal: Optional[str],
    by: str,
    draft: Optional[str],
) -> None:
    """Adds a part to QUESTION, numbered after the parts QUESTION already holds."""
    _run(
        "part add", {"question": question, "text": text, "literal": literal}, by, draft
    )


@draft_part.command("solution")
@click.argument("part")
@_text_or_literal
@_by
@_draft
def draft_part_solution(
    part: str,
    text: Optional[str],
    literal: Optional[str],
    by: str,
    draft: Optional[str],
) -> None:
    """Gives PART - q1.p2 - the worked solution written at --text or --literal."""
    _run(
        "part solution",
        {"part": part, "text": text, "literal": literal},
        by,
        draft,
    )


@draft_group.group("split")
def draft_split() -> None:
    """Cuts a block of the frozen source that holds two things."""


@draft_split.command("block")
@click.argument("block")
@click.argument("at", type=int)
@_by
@_draft
def draft_split_block(block: str, at: int, by: str, draft: Optional[str]) -> None:
    """Splits BLOCK in two, the second half starting at line AT."""
    _run("split block", {"block": block, "at": at}, by, draft)


@draft_group.group("field")
def draft_field() -> None:
    """Writes a field the draft already holds, from the source or by hand."""


@draft_field.command("replace")
@click.argument("field")
@click.argument("old")
@click.argument("new")
@click.option(
    "--regex",
    is_flag=True,
    help="Read OLD as a regular expression, and NEW as the replacement.",
)
@_by
@_draft
def draft_field_replace(
    field: str, old: str, new: str, regex: bool, by: str, draft: Optional[str]
) -> None:
    """Replaces OLD with NEW in FIELD, where OLD occurs once."""
    _run(
        "field replace",
        {"field": field, "old": old, "new": new, "regex": True if regex else None},
        by,
        draft,
    )


@draft_field.command("set")
@click.argument("field")
@click.option("--text", required=True, help=_WHERE)
@_by
@_draft
def draft_field_set(field: str, text: str, by: str, draft: Optional[str]) -> None:
    """Quotes the lines --text names into FIELD, which is already written."""
    _run("field set", {"field": field, "text": text}, by, draft)


@draft_group.command("replay")
@_draft
def draft_replay(draft: Optional[str]) -> None:
    """Rebuilds a draft from its log and checks the result matches."""
    with _message_not_traceback():
        in2lambda.draft.replay(in2lambda.source.find(draft))
    click.echo("Replays as it stands.")


@cli.group("spec")
def spec_group() -> None:
    """Runs a YAML spec of selectors over a draft's frozen source."""


@spec_group.command("run")
# The spec is named from the draft's directory, which is where `spec_command` reads it
# and how the log records it, so click does not check that the file is there.
@click.argument("spec")
@_by
@_draft
def spec_run(spec: str, by: str, draft: Optional[str]) -> None:
    """Fills the draft's fields in from SPEC, and reports the blocks left in no field."""
    with _message_not_traceback():
        path = in2lambda.source.find(draft)
        report = in2lambda.draft.execute(
            in2lambda.draft.spec_command(spec, by, path), path
        )
    click.echo(report)


@cli.command("validate")
@_draft
def validate(draft: Optional[str]) -> None:
    """Checks a draft and writes the report into it.

    Reports source blocks in no field and not marked ignore, two fields taken from the
    same lines, gaps in the numbering of the questions or their parts, and fields holding
    nothing. The set the draft describes is checked as well - maths delimiters, what
    KaTeX will not render, images the export would not carry, and the compile Lambda
    Feedback's PDF generator performs where pandoc and xelatex are installed - each
    against the field holding it. in2lambda build refuses every one of those. A question
    or part nothing answers is reported as a warning, which in2lambda build prints before
    writing the set. A finding is not a failure: the report is written into the draft,
    and the next run of the checks replaces it.
    """
    with _message_not_traceback():
        report = in2lambda.draft.report.validate(in2lambda.source.find(draft))
    for finding in report:
        # Marked in the output, because a warning and an error are acted on differently
        # and the report is often read from the terminal and not from the draft.
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
"""Where a command writes its files, named as `convert` has always named it."""


@cli.command("build")
@_out
@_draft
def build(output_dir: str, draft: Optional[str]) -> None:
    """Writes a draft out as a Lambda Feedback set.

    Refused unless in2lambda validate has run since the draft last changed and found no
    error, so that the set uploaded is the set the checks have read. A finding at level
    warning - a question or part with no solution written for it - is printed, and the
    set is written all the same.
    """
    with _message_not_traceback(), _warnings_said():
        written = in2lambda.draft.export.build(
            in2lambda.source.find(draft), output_dir=output_dir
        )
    click.echo(f"Wrote {written}")


@cli.command("render")
@_out
@_draft
def render(output_dir: str, draft: Optional[str]) -> None:
    """Writes each question of a draft as a PDF, for review.

    The questions are compiled as Lambda Feedback's PDF generator compiles them, which
    needs pandoc and xelatex. in2lambda render does not read the draft's report: a draft
    is rendered to be read, including a draft with something to fix in it.
    """
    # A question xelatex complains about is written out all the same, and what xelatex
    # refused is printed as a line and not as a traceback.
    with _message_not_traceback(), _warnings_said():
        written = in2lambda.draft.export.render(
            in2lambda.source.find(draft), output_dir=output_dir
        )
    for pdf in written:
        click.echo(f"Wrote {pdf}")


def _set_at(path: str) -> Set:
    """The set at `path`, or a message naming `path` where it holds no set.

    `Set.from_json` raises `ValueError` where a folder or a zip holds no ``set_*.json``,
    and `zipfile.BadZipFile` where a path named ``.zip`` is not a zip at all. `compare`
    reads two paths, so the message names which of the two is at fault.
    """
    try:
        return Set.from_json(path)
    except (ValueError, zipfile.BadZipFile):
        raise click.ClickException(
            f"{path} is not a Lambda Feedback set. A set is a folder or a zip holding "
            "one set_*.json file beside a question_*.json file per question."
        ) from None


@cli.command("compare")
@click.argument("built_zip", type=click.Path(exists=True))
@click.argument("export_dir", type=click.Path(exists=True))
@click.option(
    "--known",
    "known_path",
    type=click.Path(exists=True, dir_okay=False),
    help="File naming the differences the two sets are known to have, one per line.",
)
def compare(built_zip: str, export_dir: str, known_path: Optional[str]) -> None:
    """Compares the set in BUILT_ZIP with the set in EXPORT_DIR, and prints each difference.

    Each argument is a Lambda Feedback set, as a folder or as a zip. Each question's main
    text is compared, and each part's text and worked solution, and every difference is
    printed naming the question, the part and the field. The differences in wording that
    are not differences in what a question says are taken off both sides first: a run of
    whitespace is compared as one space, a line of hyphens is dropped, a curly quote is
    compared as a straight quote, an HTML entity for a space is compared as a space, the
    notation inside maths and the whitespace beside it are dropped, an image is compared
    by the file's name, and a lone empty part is dropped. in2lambda.compare says which
    notation and why. --known names a file of the differences the two sets are known to
    have, one per line as this command prints it, with a ticket written after "  # ".
    in2lambda compare exits 1 where the differences found are not the differences --known
    names.
    """
    with _message_not_traceback():
        found = in2lambda.compare.differences(
            _set_at(built_zip),
            _set_at(export_dir),
            left_name=built_zip,
            right_name=export_dir,
        )
    for line in found:
        click.echo(line)

    expected = in2lambda.compare.known(known_path) if known_path else []
    if found == expected:
        if not found:
            click.echo("Identical.")
        return
    # Echoed rather than put in the message, because a difference is a long line and
    # the message is printed in a box that wraps it.
    for line in expected:
        if line not in found:
            click.echo(f"Not found: {line}")
    if not known_path:
        raise click.ClickException(
            "The two sets differ in the places printed above. Pass --known FILE to "
            "name the differences the two sets are known to have."
        )
    raise click.ClickException(
        f"The differences printed above are not the differences {known_path} names. "
        f"Write one line of {known_path} per difference found, with the ticket that "
        'would close it after "  # ".'
    )


if __name__ == "__main__":
    cli()
