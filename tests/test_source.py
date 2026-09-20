"""Freezing a source document, and what happens when it changes afterwards.

Each folder in ``fixtures/sources`` is one document beside the block list freezing it
should produce, so covering another construct means adding a folder rather than a test.
The rest is what the command line does - printing a draft, and refusing one whose source
has moved on or which nothing here wrote - which is not something a fixture can say.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import SOURCES, SOURCES_DIR

from in2lambda.draft import _quoted
from in2lambda.main import cli
from in2lambda.validation import MathDelimiterError, math_delimiter_checker

MARKDOWN = SOURCES_DIR / "markdown"
"""The case the tests below happen to use; what they check holds for any of them."""


def _frozen(directory: Path) -> Path:
    """The document a folder holds, whatever format it is in."""
    (source,) = (path for path in directory.iterdir() if path.stem == "source")
    return source


@pytest.mark.parametrize("folder", SOURCES, ids=lambda path: path.name)
def test_source_add_finds_the_expected_blocks(folder: Path, tmp_path: Path) -> None:
    """Each document freezes to the block list written beside it, hash and all."""
    shutil.copytree(folder, tmp_path, dirs_exist_ok=True)

    result = CliRunner().invoke(cli, ["source", "add", str(_frozen(tmp_path))])

    assert result.exit_code == 0, result.output
    draft = json.loads((tmp_path / "source.draft.json").read_text())
    (source,) = draft["sources"]
    assert source["blocks"] == json.loads((folder / "expected.json").read_text())
    raw = (tmp_path / source["source"]).read_bytes()
    assert source["hash"] == f"sha256:{hashlib.sha256(raw).hexdigest()}"

    # Every block is a range some command will quote, and what it quotes is a field
    # `draft validate` runs the delimiter checks over. A freeze that kept pandoc's own
    # wrapping, or the `$$ ... $$` its writer puts on one line, would hand those checks
    # a finding about the writer rather than about the document.
    markdown = raw.decode("utf-8")
    for block in source["blocks"]:
        quoted = _quoted(draft, markdown, 1, block["start"], block["end"])
        assert math_delimiter_checker(quoted) is MathDelimiterError.PASSED, quoted


def test_freezing_again_is_refused_once_the_source_has_changed(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft is only an address for line ranges while the lines have not moved."""
    monkeypatch.setenv("COLUMNS", "200")  # So the message is not wrapped mid-sentence.
    source = tmp_path / "source.md"
    shutil.copy(_frozen(MARKDOWN), source)
    runner = CliRunner()
    assert runner.invoke(cli, ["source", "add", str(source)]).exit_code == 0
    frozen = (tmp_path / "source.draft.json").read_text()

    # Freezing the same file again changes nothing, so it is allowed.
    assert runner.invoke(cli, ["source", "add", str(source)]).exit_code == 0
    assert (tmp_path / "source.draft.json").read_text() == frozen

    source.write_text(f"{source.read_text()}\nAn afterthought.\n")
    result = runner.invoke(cli, ["source", "add", str(source)])

    assert result.exit_code != 0
    assert "--start-over" in result.output
    assert (tmp_path / "source.draft.json").read_text() == frozen

    assert (
        runner.invoke(cli, ["source", "add", str(source), "--start-over"]).exit_code
        == 0
    )
    assert (tmp_path / "source.draft.json").read_text() != frozen


def test_a_markdown_file_no_draft_claims_is_not_overwritten(
    tmp_path: Path, monkeypatch
) -> None:
    """Freezing a .tex writes a .md beside it, which may be someone else's work."""
    monkeypatch.setenv("COLUMNS", "200")
    shutil.copy(_frozen(SOURCES_DIR / "tex"), tmp_path / "source.tex")
    theirs = "# Notes I wrote by hand\n"
    (tmp_path / "source.md").write_text(theirs)
    runner = CliRunner()

    result = runner.invoke(cli, ["source", "add", str(tmp_path / "source.tex")])

    assert result.exit_code != 0
    assert "--start-over" in result.output
    assert (tmp_path / "source.md").read_text() == theirs
    assert not (tmp_path / "source.draft.json").exists()

    # Saying to start over is saying to overwrite it.
    result = runner.invoke(
        cli, ["source", "add", str(tmp_path / "source.tex"), "--start-over"]
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "source.md").read_text() != theirs
    draft = json.loads((tmp_path / "source.draft.json").read_text())
    assert [source["source"] for source in draft["sources"]] == ["source.md"]


def test_source_show_numbers_the_lines_and_names_the_blocks(
    tmp_path: Path, monkeypatch
) -> None:
    """`source show` is how someone checks the ids the agent will be quoting."""
    shutil.copytree(MARKDOWN, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["source", "add", str(_frozen(tmp_path))])

    result = runner.invoke(cli, ["source", "show"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    markdown = (tmp_path / "source.md").read_text().splitlines()
    assert lines[0] == f"b1   1  {markdown[0]}"
    assert lines[1] == "     2"  # A blank line still gets its number, with no id.
    assert len(lines) == len(markdown)

    # Every block's id sits on the line it starts at, and nothing else carries one.
    blocks = json.loads((tmp_path / "source.draft.json").read_text())["sources"][0][
        "blocks"
    ]
    for block in blocks:
        assert lines[block["start"] - 1].split()[0] == block["id"]
    assert sum(bool(re.match(r" *b\d+ ", line)) for line in lines) == len(blocks)


def test_a_second_source_is_frozen_beside_the_first(
    tmp_path: Path, monkeypatch
) -> None:
    """A sheet and the solutions written separately from it are two sources of a draft."""
    shutil.copy(_frozen(MARKDOWN), tmp_path / "source.md")
    (tmp_path / "solutions.md").write_text("# Solutions\n\n1. The load is $F = pA$.\n")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["source", "add", "source.md"]).exit_code == 0

    # A file the draft beside it has not got is the next source, not a second freezing.
    assert (
        runner.invoke(
            cli, ["source", "add", "solutions.md", "--draft", "source.md"]
        ).exit_code
        == 0
    )

    draft = json.loads((tmp_path / "source.draft.json").read_text())
    assert [source["source"] for source in draft["sources"]] == [
        "source.md",
        "solutions.md",
    ]
    # Every id of a source after the first says which source it is an id of.
    assert [block["id"] for block in draft["sources"][1]["blocks"]] == ["2/b1", "2/b2"]
    # And naming both files freezes neither again, as naming one already frozen does not.
    written = (tmp_path / "source.draft.json").read_bytes()
    result = runner.invoke(cli, ["source", "add", "source.md", "solutions.md"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "source.draft.json").read_bytes() == written

    result = runner.invoke(cli, ["source", "show"])

    assert result.exit_code == 0, result.output
    # Each source under its number and its name, since both start their lines at 1.
    assert "Source 1: source.md" in result.output
    assert "Source 2: solutions.md" in result.output
    assert "2/b1  1  # Solutions" in result.output


def test_freezing_files_from_two_directories_is_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft sits beside its sources, so there is no one draft for files apart."""
    monkeypatch.setenv("COLUMNS", "200")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    shutil.copy(_frozen(MARKDOWN), tmp_path / "source.md")
    (elsewhere / "solutions.md").write_text("# Solutions\n")

    result = CliRunner().invoke(
        cli,
        ["source", "add", str(tmp_path / "source.md"), str(elsewhere / "solutions.md")],
    )

    assert result.exit_code != 0
    assert "same directory" in result.output
    assert not (tmp_path / "source.draft.json").exists()


def test_source_show_without_a_draft_says_so(tmp_path: Path, monkeypatch) -> None:
    """Running it in the wrong directory is a message, not a traceback."""
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["source", "show"])

    assert result.exit_code != 0
    assert "in2lambda source add" in result.output
    assert isinstance(result.exception, SystemExit)


def test_source_show_refuses_once_the_source_has_changed(
    tmp_path: Path, monkeypatch
) -> None:
    """Ids printed against lines they are not the ids of would look right and be wrong."""
    monkeypatch.setenv("COLUMNS", "200")
    shutil.copytree(MARKDOWN, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["source", "add", "source.md"]).exit_code == 0

    source = tmp_path / "source.md"
    source.write_text(f"An afterthought.\n\n{source.read_text()}")
    result = runner.invoke(cli, ["source", "show"])

    assert result.exit_code != 0
    assert "--start-over" in result.output
    assert isinstance(result.exception, SystemExit)


@pytest.mark.parametrize(
    "content",
    ["{ not json at all", '{"blocks": []}', '{"sources": [], "log": [], "fields": {}}'],
    ids=["not-json", "foreign", "no-sources"],
)
@pytest.mark.parametrize(
    "arguments",
    [
        ["source", "add", "source.md"],
        ["source", "show"],
        ["draft", "mark", "ignore", "b1"],
        ["draft", "replay"],
    ],
    ids=["add", "show", "mark", "replay"],
)
def test_a_draft_from_somewhere_else_is_refused(
    content: str, arguments: list[str], tmp_path: Path, monkeypatch
) -> None:
    """A draft nothing here wrote is neither read from nor written over."""
    monkeypatch.setenv("COLUMNS", "200")
    shutil.copy(_frozen(MARKDOWN), tmp_path / "source.md")
    (tmp_path / "source.draft.json").write_text(content)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code != 0
    assert "--start-over" in result.output
    assert isinstance(result.exception, SystemExit)
    assert (tmp_path / "source.draft.json").read_text() == content


def test_a_frozen_file_that_has_gone_is_a_message(tmp_path: Path, monkeypatch) -> None:
    """The draft names the markdown, and someone may well have moved it since."""
    monkeypatch.setenv("COLUMNS", "200")
    shutil.copytree(MARKDOWN, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(cli, ["source", "add", "source.md"]).exit_code == 0
    (tmp_path / "source.md").unlink()

    result = runner.invoke(cli, ["source", "show"])

    assert result.exit_code != 0
    assert "source.md" in result.output
    assert isinstance(result.exception, SystemExit)


def test_a_source_that_is_not_text_is_a_message(tmp_path: Path, monkeypatch) -> None:
    """A .md saved in some other encoding cannot be read as markdown, and says so."""
    monkeypatch.setenv("COLUMNS", "200")
    source = tmp_path / "source.md"
    source.write_bytes(b"\xff\xfe# Hydraulic scale\n")

    result = CliRunner().invoke(cli, ["source", "add", str(source)])

    assert result.exit_code != 0
    assert "UTF-8" in result.output
    assert isinstance(result.exception, SystemExit)
    assert not (tmp_path / "source.draft.json").exists()
