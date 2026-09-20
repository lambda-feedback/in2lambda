"""Freezing a source document, and what happens when it changes afterwards.

Each folder in ``fixtures/sources`` is one document beside the block list freezing it
should produce, so covering another construct means adding a folder rather than a test.
The rest is what the command line does - refusing a draft whose source has moved on,
and printing one - which is not something a fixture can say.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import SOURCES, SOURCES_DIR

from in2lambda.main import cli

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
    draft = json.loads((tmp_path / "draft.json").read_text())
    assert draft["blocks"] == json.loads((folder / "expected.json").read_text())
    markdown = (tmp_path / draft["source"]).read_bytes()
    assert draft["hash"] == f"sha256:{hashlib.sha256(markdown).hexdigest()}"


def test_freezing_again_is_refused_once_the_source_has_changed(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft is only an address for line ranges while the lines have not moved."""
    monkeypatch.setenv("COLUMNS", "200")  # So the message is not wrapped mid-sentence.
    source = tmp_path / "source.md"
    shutil.copy(_frozen(MARKDOWN), source)
    runner = CliRunner()
    assert runner.invoke(cli, ["source", "add", str(source)]).exit_code == 0
    frozen = (tmp_path / "draft.json").read_text()

    # Freezing the same file again changes nothing, so it is allowed.
    assert runner.invoke(cli, ["source", "add", str(source)]).exit_code == 0
    assert (tmp_path / "draft.json").read_text() == frozen

    source.write_text(f"{source.read_text()}\nAn afterthought.\n")
    result = runner.invoke(cli, ["source", "add", str(source)])

    assert result.exit_code != 0
    assert "--start-over" in result.output
    assert (tmp_path / "draft.json").read_text() == frozen

    assert (
        runner.invoke(cli, ["source", "add", str(source), "--start-over"]).exit_code
        == 0
    )
    assert (tmp_path / "draft.json").read_text() != frozen


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


def test_source_show_without_a_draft_says_so(tmp_path: Path, monkeypatch) -> None:
    """Running it in the wrong directory is a message, not a traceback."""
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["source", "show"])

    assert result.exit_code != 0
    assert "in2lambda source add" in result.output
    assert isinstance(result.exception, SystemExit)
