"""Takes one document down both routes and compares what each makes of it.

`in2lambda convert` reads a document with a filter and writes a set. The draft workflow
freezes the same document, fills a draft's fields in from it, checks the draft over and
builds the set from the fields. Each folder in ``fixtures/against_convert`` is one
document put through both, so that a difference between the two is a test failure rather
than something a first real run finds. The folder's README says which documents are here,
which are not, and what the comparison leaves out.

The zip a draft builds is also compared with the real exports in ``fixtures/exports``, and
each draft is replayed from its log, so that one run covers what the route writes as well
as what it says.
"""

import json
import shutil
import tempfile
import warnings
from functools import cache
from itertools import zip_longest
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import (
    AGAINST_CONVERT,
    AGAINST_CONVERT_DIR,
    EXPORTS,
    SOURCES_DIR,
    key_paths,
    needs_compiler,
    unexported_keys,
)

import in2lambda.draft
import in2lambda.draft.report
import in2lambda.source
from in2lambda.api.question import Question
from in2lambda.api.set import Set
from in2lambda.filters import builtin_filters
from in2lambda.json_convert.json_convert import _IMAGE
from in2lambda.main import cli, runner
from in2lambda.validation import _location
from in2lambda.validation.delimiters import MathDelimiterError

# Both routes compile the set and render its maths, which is what the two are being
# compared over, so a machine without the toolchain runs none of this.
pytestmark = needs_compiler

each_folder = pytest.mark.parametrize(
    "folder", AGAINST_CONVERT, ids=lambda path: path.name
)

PARTS_ONE_SOL = AGAINST_CONVERT_DIR / "PartsOneSol"
"""The one folder whose document writes a worked solution, which its filter drops."""

_INLINE_DISPLAY = MathDelimiterError.MISSING_NEWLINE_AFTER_OPENING_DISPLAY.value
"""What the checks report over ``$$x$$`` on one line, which is what t44 is about."""

_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})
"""Pandoc's LaTeX reader writes typographic quotes; its commonmark_x writer writes ASCII."""


@cache
def _display_maths_frozen_inline() -> bool:
    """Whether `source add` writes display maths on one line, which `build` refuses.

    Pandoc's commonmark_x writer puts ``$$x = y$$`` on one line, and
    `in2lambda.validation.delimiters` reports that as an error, so a draft quoting a
    block of display maths cannot be built until t44 writes it in block form. This is
    asked of a document here rather than answered by naming the folders it applies to,
    so that those folders run as they stand once t44 is in.
    """
    with tempfile.TemporaryDirectory() as directory:
        probe = Path(directory) / "probe.tex"
        probe.write_text(
            "\\documentclass{article}\n\\begin{document}\n\\[ x = y \\]\n"
            "\\end{document}\n"
        )
        _, sources = in2lambda.source.frozen(in2lambda.source.add([str(probe)]))
        return "$$x = y$$" in sources[0]


def _document(folder: Path, tmp_path: Path, filters_dir: str) -> tuple[Path, str]:
    """Copies the document a folder is about into `tmp_path`, with the files beside it.

    A folder named after a filter is about the ``example.tex`` that filter ships, read
    with that filter; the figures the example refers to are copied with it. Any other
    folder is named after a folder of ``fixtures/sources``, and is read with PartsOneSol.
    """
    if folder.name in builtin_filters():
        shutil.copytree(Path(filters_dir) / folder.name, tmp_path, dirs_exist_ok=True)
        return tmp_path / "example.tex", folder.name
    shutil.copytree(SOURCES_DIR / folder.name, tmp_path, dirs_exist_ok=True)
    (source,) = tmp_path.glob("source.*")
    return source, "PartsOneSol"


def _built(folder: Path, tmp_path: Path, filters_dir: str) -> tuple[Path, Path, str]:
    """A folder's document in `tmp_path`, with its draft built, checked and exported.

    Returns:
        The draft, the document it was frozen from, and the filter `in2lambda convert`
        reads that document with. The set is in ``out/set`` beside them, and the zip
        Lambda Feedback imports is ``out/set.zip``.
    """
    source, layout = _document(folder, tmp_path, filters_dir)
    cli_runner = CliRunner()
    assert cli_runner.invoke(cli, ["source", "add", source.name]).exit_code == 0
    draft_path = tmp_path / f"{source.stem}.draft.json"

    if (spec := folder / "spec.yaml").is_file():
        shutil.copy(spec, tmp_path)
        in2lambda.draft.execute(
            in2lambda.draft.spec_command(spec.name, "tests", draft_path), draft_path
        )
    else:
        for entry in json.loads((folder / "commands.json").read_text()):
            in2lambda.draft.execute(entry, draft_path)

    with warnings.catch_warnings(record=True) as said:
        warnings.simplefilter("always")
        report = in2lambda.draft.report.validate(draft_path)
    if _display_maths_frozen_inline() and any(
        _INLINE_DISPLAY in finding["message"] for finding in report
    ):
        pytest.skip("t44: display maths is frozen inline")
    # The checks compile the set and render its maths, which is two of the stages this
    # test is about, so a run that reported neither has not been over them.
    missing = [
        str(warning.message) for warning in said if "install" in str(warning.message)
    ]
    assert not missing, missing

    result = cli_runner.invoke(cli, ["build"])
    assert result.exit_code == 0, result.output
    return draft_path, source, layout


def _text(markdown: str) -> str:
    """A field as both routes say it, with the three differences in wording taken off.

    An image reference is compared by the file's name: convert writes the alt text
    ``pictureTag`` where the draft keeps the alt text the document wrote, and the
    exported set names the file as it sits in ``media/`` where the set convert returns
    still holds the path the document wrote. The draft also quotes the lines pandoc
    wrapped where convert writes a paragraph on one line, and the two readers write
    quotes differently. The folder's README says all of them.
    """
    named = _IMAGE.sub(lambda reference: f"![]({Path(reference[1]).name})", markdown)
    return " ".join(named.translate(_QUOTES).split())


def _parts(question: Question) -> list[str]:
    """Each part's text, dropping a lone part that has none.

    A question the draft writes without parts exports as one part holding nothing,
    because Lambda Feedback's template fills a question holding no part with placeholder
    wording. Convert writes no part at all. The empty part says nothing either way.
    """
    texts = [_text(part.text) for part in question.parts]
    return [] if texts == [""] else texts


def _same(drafted: Set, converted: Set) -> None:
    """Raises unless both sets say the same thing, naming the first place they differ.

    Args:
        drafted: The set built from a draft, as `Set.from_json` reads its zip.
        converted: The set `in2lambda convert` made of the same document.

    Raises:
        AssertionError: the two hold a different number of questions or parts, or one
            question or part says something the other does not. The message names the
            question, the part and the field as `in2lambda.validation` names them.
    """
    questions = zip_longest(drafted.questions, converted.questions)
    for number, (draft_question, convert_question) in enumerate(questions, start=1):
        where = _location(number, "")
        assert (
            draft_question is not None
        ), f"{where}: convert wrote this question and the draft did not"
        assert (
            convert_question is not None
        ), f"{where}: the draft wrote this question and convert did not"

        drafted_text = _text(draft_question.main_text)
        converted_text = _text(convert_question.main_text)
        assert drafted_text == converted_text, (
            f"{_location(number, '', field='main text')}: the draft says "
            f"{drafted_text!r} and convert says {converted_text!r}"
        )

        texts = zip_longest(_parts(draft_question), _parts(convert_question))
        for index, (draft_part, convert_part) in enumerate(texts):
            part = _location(number, "", index, "text")
            assert (
                draft_part is not None
            ), f"{part}: convert wrote this part and the draft did not"
            assert (
                convert_part is not None
            ), f"{part}: the draft wrote this part and convert did not"
            assert draft_part == convert_part, (
                f"{part}: the draft says {draft_part!r} and convert says "
                f"{convert_part!r}"
            )


@each_folder
def test_the_draft_route_agrees_with_convert(
    folder: Path, tmp_path: Path, filters_dir: str, monkeypatch
) -> None:
    """Both routes make the same questions and parts of the same document."""
    monkeypatch.chdir(tmp_path)
    _, source, layout = _built(folder, tmp_path, filters_dir)

    try:
        converted = runner(str(source), layout)
    except UnicodeDecodeError:
        # `image_directories` opens the document as UTF-8 text to look for a
        # \graphicspath, so convert raises this over every .docx holding an image. The
        # draft route reads the same document, which is how this test found it.
        pytest.xfail("convert reads the document as text to find \\graphicspath")

    _same(Set.from_json(str(tmp_path / "out" / "set.zip")), converted)


@each_folder
def test_the_written_keys_exist_in_a_real_export(
    folder: Path, tmp_path: Path, filters_dir: str, monkeypatch
) -> None:
    """A draft's zip holds no key, at any depth, that Lambda Feedback never exports.

    `test_exports` asks this of a set written back from the export it was read from.
    A draft's set is written from its fields, and no export stands behind it, so every
    key of it is looked for in the union of every export in ``fixtures/exports``.
    """
    monkeypatch.chdir(tmp_path)
    _built(folder, tmp_path, filters_dir)

    exported = set().union(
        *(
            key_paths(json.loads(file.read_text()))
            for export_dir in EXPORTS
            for file in export_dir.glob("*.json")
        )
    )
    missing = {}
    for file in (tmp_path / "out" / "set").glob("*.json"):
        keys = unexported_keys(json.loads(file.read_text()), exported)
        if keys:
            missing[file.name] = keys
    assert not missing, missing


@each_folder
def test_the_draft_replays(
    folder: Path, tmp_path: Path, filters_dir: str, monkeypatch
) -> None:
    """The log of a draft built and checked this way rebuilds it, byte for byte."""
    monkeypatch.chdir(tmp_path)
    draft_path, _, _ = _built(folder, tmp_path, filters_dir)
    written = draft_path.read_bytes()

    result = CliRunner().invoke(cli, ["draft", "replay"])

    assert result.exit_code == 0, result.output
    assert draft_path.read_bytes() == written


def test_the_draft_holds_the_solutions_convert_drops(
    tmp_path: Path, filters_dir: str, monkeypatch
) -> None:
    """The draft writes both solution environments that the PartsOneSol filter drops.

    That filter matches a Div only when its first element stringifies to ``Solution``,
    which pandoc writes for no solution environment, so convert exports the layout's
    examples with no worked solution at all. Fixing it is t52; this says what each route
    does with the same two environments in the meantime.
    """
    monkeypatch.chdir(tmp_path)
    draft_path, source, layout = _built(PARTS_ONE_SOL, tmp_path, filters_dir)

    fields = json.loads(draft_path.read_text())["fields"]
    assert "The solution is copied across all parts." in fields["q1.solution"]["value"]
    assert fields["q2.solution"]["value"] == "And here's the solution"
    assert not [
        part
        for question in runner(str(source), layout).questions
        for part in question.parts
        if part.worked_solution
    ]


def test_a_spec_that_swaps_part_and_solution_is_caught(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft that says something else about a question fails, naming that question.

    The four folders agree, so a comparison that could not tell them from a draft built
    wrongly would pass them as well. The spec here reads each solution as the part and
    each part as the solution.
    """
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source.md"
    source.write_text(
        "# Hydraulics\n\n"
        "Q1. Find the load the large piston carries.\n\n"
        "1.  State the pressure under the small piston.\n\n"
        "::: {.solution}\n$F = pA$.\n:::\n"
    )
    (tmp_path / "spec.yaml").write_text(
        "question: Para\n"
        "part:     Div\n"
        "solution: ListItem\n"
        "strip:    ['(?m)^::: \\{\\.solution\\}\\n', '(?m)^:::$']\n"
        "ignore:   Header\n"
        "layout:   PartsOneSol\n"
    )
    cli_runner = CliRunner()
    assert cli_runner.invoke(cli, ["source", "add", "source.md"]).exit_code == 0
    draft_path = tmp_path / "source.draft.json"
    in2lambda.draft.execute(
        in2lambda.draft.spec_command("spec.yaml", "tests", draft_path), draft_path
    )
    in2lambda.draft.report.validate(draft_path)
    assert cli_runner.invoke(cli, ["build"]).exit_code == 0

    with pytest.raises(AssertionError, match='Question 1 "", part \\(a\\), text'):
        _same(
            Set.from_json(str(tmp_path / "out" / "set.zip")),
            runner(str(source), "PartsOneSol"),
        )
