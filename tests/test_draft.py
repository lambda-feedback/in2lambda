"""Building a draft by commands, and rebuilding it from the ones it recorded.

Each folder in ``fixtures/drafts`` is a document, the commands to run against its draft
and the fields they should write, so covering another command means adding a folder
rather than a test. The rest is what the command line does when a replay cannot be
trusted - a source that has moved on, a log naming a command nothing has, a draft edited
by hand - which is not something a fixture can say.
"""

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import DRAFTS, DRAFTS_DIR

import in2lambda.draft
from in2lambda.main import cli

MARK_IGNORE = DRAFTS_DIR / "mark_ignore"
"""The case the tests below happen to use; what they check holds for any of them."""


def _built(folder: Path, tmp_path: Path) -> Path:
    """A folder's document, frozen in `tmp_path` with its commands applied to it."""
    shutil.copytree(folder, tmp_path, dirs_exist_ok=True)
    assert CliRunner().invoke(cli, ["source", "add", "source.md"]).exit_code == 0
    for entry in json.loads((folder / "commands.json").read_text()):
        in2lambda.draft.execute(entry)
    return tmp_path / "draft.json"


@pytest.mark.parametrize("folder", DRAFTS, ids=lambda path: path.name)
def test_a_draft_built_by_commands_replays_identically(
    folder: Path, tmp_path: Path, monkeypatch
) -> None:
    """A run is only reproducible if the log rebuilds the same draft, byte for byte."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(folder, tmp_path)

    draft = json.loads(draft_path.read_text())
    assert draft["fields"] == json.loads((folder / "expected.json").read_text())
    assert draft["log"] == json.loads((folder / "commands.json").read_text())

    written = draft_path.read_bytes()
    result = CliRunner().invoke(cli, ["draft", "replay"])

    assert result.exit_code == 0, result.output
    assert draft_path.read_bytes() == written


def test_a_command_and_a_replay_are_refused_once_the_source_has_changed(
    tmp_path: Path, monkeypatch
) -> None:
    """Commands were run against lines that have moved, so neither is an address now."""
    monkeypatch.setenv("COLUMNS", "200")  # So the message is not wrapped mid-sentence.
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    built = draft_path.read_bytes()
    source = tmp_path / "source.md"
    source.write_text(f"An afterthought.\n\n{source.read_text()}")
    runner = CliRunner()

    for arguments in (["draft", "replay"], ["draft", "mark", "ignore", "b2"]):
        result = runner.invoke(cli, arguments)

        assert result.exit_code != 0, arguments
        assert "--start-over" in result.output
        assert draft_path.read_bytes() == built


def test_a_log_naming_a_command_nothing_has_is_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft from a newer in2lambda cannot be rebuilt here, and says which command."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    draft = json.loads(draft_path.read_text())
    draft["log"].append({"command": "frobnicate", "args": {}, "by": "tests"})
    draft_path.write_text(json.dumps(draft))

    result = CliRunner().invoke(cli, ["draft", "replay"])

    assert result.exit_code != 0
    assert "frobnicate" in result.output


def test_a_field_changed_by_hand_is_refused(tmp_path: Path, monkeypatch) -> None:
    """What is in a draft has to have come from the commands it records, or it is lost."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    draft = json.loads(draft_path.read_text())
    draft["fields"]["b1.ignore"]["value"] = False
    edited = json.dumps(draft, indent=2, sort_keys=True) + "\n"
    draft_path.write_text(edited)

    result = CliRunner().invoke(cli, ["draft", "replay"])

    assert result.exit_code != 0
    assert "does not reproduce" in result.output
    # A replay says what it found; writing the answer is how the edit would be lost.
    assert draft_path.read_text() == edited


def test_marking_a_block_that_is_not_there_says_so(tmp_path: Path, monkeypatch) -> None:
    """The ids come from `source show`, and a typo in one is a message, not a field."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    built = draft_path.read_bytes()

    result = CliRunner().invoke(cli, ["draft", "mark", "ignore", "b99"])

    assert result.exit_code != 0
    assert "b99" in result.output
    assert "in2lambda source show" in result.output
    assert draft_path.read_bytes() == built
