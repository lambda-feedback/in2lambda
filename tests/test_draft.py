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
from typing import Any

import pytest
from click.testing import CliRunner
from conftest import DRAFTS, DRAFTS_DIR

import in2lambda.draft
from in2lambda.main import cli

MARK_IGNORE = DRAFTS_DIR / "mark_ignore"
"""The case the tests below happen to use; what they check holds for any of them."""

TWO_QUESTIONS = DRAFTS_DIR / "two_questions"
"""The one with questions written into it, which is what refusing a second one needs."""


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


@pytest.mark.parametrize("folder", DRAFTS, ids=lambda path: path.name)
def test_freezing_an_unchanged_source_again_keeps_what_the_commands_wrote(
    folder: Path, tmp_path: Path, monkeypatch
) -> None:
    """The lines have not moved, so the commands run against them still hold.

    Over every folder rather than one of them, because a command that changes the blocks
    rather than the fields - `split block` - is only kept if the draft is not rebuilt.
    """
    monkeypatch.chdir(tmp_path)
    draft_path = _built(folder, tmp_path)
    built = draft_path.read_bytes()
    runner = CliRunner()

    assert runner.invoke(cli, ["source", "add", "source.md"]).exit_code == 0
    assert draft_path.read_bytes() == built

    # Which leaves --start-over as the way to be rid of them.
    assert (
        runner.invoke(cli, ["source", "add", "source.md", "--start-over"]).exit_code
        == 0
    )
    draft = json.loads(draft_path.read_text())
    assert (draft["log"], draft["fields"]) == ([], {})


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


@pytest.mark.parametrize(
    ("entry", "named"),
    [
        ("mark ignore b2", "mark ignore b2"),
        ({"command": "mark ignore", "args": {"block": "b2"}}, "by"),
        ({"command": 7, "args": {}, "by": "tests"}, "7"),
        ({"command": "mark ignore", "args": "b2", "by": "tests"}, "b2"),
        ({"command": "mark ignore", "args": None, "by": "tests"}, "None"),
        ({"command": "mark ignore", "args": [], "by": "tests"}, "[]"),
        ({"command": "mark ignore", "args": {}, "by": "tests"}, "block"),
        (
            {
                "command": "question add",
                "args": {"text": "s1", "literal": "Words."},
                "by": "tests",
            },
            "literal",
        ),
        ({"command": "split block", "args": {"block": "b2"}, "by": "tests"}, "at"),
        ({"command": "mark ignore", "args": {"block": 12}, "by": "tests"}, "12"),
        ({"command": "question add", "args": {"text": 12}, "by": "tests"}, "12"),
    ],
    ids=[
        "not an object",
        "no by",
        "command is not a name",
        "args is not an object",
        "args is null",
        "args is a list",
        "no block argument",
        "both a text and a literal",
        "no at argument",
        "a block that is a number",
        "a text that is a number",
    ],
)
def test_a_log_entry_that_is_not_a_command_is_refused(
    entry: Any, named: str, tmp_path: Path, monkeypatch
) -> None:
    """A log anyone can edit is not a shape to assume, and a bad one is not a crash."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    draft = json.loads(draft_path.read_text())
    draft["log"].append(entry)
    draft_path.write_text(json.dumps(draft))

    result = CliRunner().invoke(cli, ["draft", "replay"])

    assert result.exit_code != 0
    assert "is not a command" in result.output
    # Which of the things wrong with it, rather than leaving the reader to guess.
    assert named in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("log", 5),
        ("fields", []),
        ("fields", {"b1.ignore": 5}),
        ("fields", {"b1.ignore": {"ranges": "s1"}}),
        ("fields", {"b1.ignore": {"ranges": [[1]]}}),
    ],
    ids=[
        "log",
        "fields",
        "a field that is a number",
        "ranges that are not a list",
        "a range that is not a pair",
    ],
)
@pytest.mark.parametrize(
    "arguments",
    [["draft", "replay"], ["draft", "mark", "ignore", "b2"]],
    ids=["replay", "mark"],
)
def test_a_draft_whose_log_or_fields_is_the_wrong_shape_is_refused(
    field: str, value: Any, arguments: list[str], tmp_path: Path, monkeypatch
) -> None:
    """A draft is a file anyone can edit, so nothing reading one assumes its shape."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    draft = json.loads(draft_path.read_text())
    draft[field] = value
    edited = json.dumps(draft, indent=2, sort_keys=True) + "\n"
    draft_path.write_text(edited)

    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code != 0
    assert field in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert draft_path.read_text() == edited


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


def test_lines_another_field_was_taken_from_are_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """Two fields of the same lines is a mistake about one of them, so neither is guessed."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)
    built = draft_path.read_bytes()

    # Line 16 is where q1's solution came from, so it is not also a third question.
    result = CliRunner().invoke(cli, ["draft", "question", "add", "--text", "s16"])

    assert result.exit_code != 0
    # Both halves of it: which field has the lines, and which one wanted them.
    assert "q1.solution" in result.output
    assert "q3.text" in result.output
    assert draft_path.read_bytes() == built


@pytest.mark.parametrize(
    ("arguments", "named"),
    [
        (["draft", "question", "add", "--text", "s99:100"], "s99:100"),
        (["draft", "question", "add", "--text", "s6:5"], "s6:5"),
        (["draft", "question", "add", "--text", "sixteen"], "sixteen"),
        (["draft", "question", "add", "--text", "s8", "--literal", "Words."], "both"),
        (["draft", "question", "add"], "neither"),
        (["draft", "part", "add", "q9", "--text", "s8"], "q9"),
        (["draft", "split", "block", "b3", "5"], "b3 is lines 5-6"),
        (["draft", "split", "block", "b3", "7"], "b3 is lines 5-6"),
    ],
    ids=[
        "lines the source has not got",
        "a range that runs backwards",
        "a text that is no kind of address",
        "a text and a literal",
        "no text and no literal",
        "a question nothing has written",
        "a split at the line the block starts on",
        "a split past the line it ends on",
    ],
)
def test_a_command_naming_what_the_draft_has_not_got_is_refused(
    arguments: list[str], named: str, tmp_path: Path, monkeypatch
) -> None:
    """Every one of these is a typo, and a typo is a message rather than a field."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)
    built = draft_path.read_bytes()

    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code != 0, result.output
    assert named in result.output
    assert draft_path.read_bytes() == built


def test_a_command_says_what_it_wrote(tmp_path: Path, monkeypatch) -> None:
    """What a command wrote is what the next one names, so it is said rather than hunted."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["draft", "question", "add", "--literal", "Words."])

    assert result.exit_code == 0, result.output
    assert result.output == "Wrote q3.text.\n"
    # And the field of that name, so that what is said and what is written cannot part.
    field = json.loads(draft_path.read_text())["fields"]["q3.text"]
    assert (field["value"], field["layer"]) == ("Words.", 4)

    # A split writes no field, so what it names is the two blocks it left behind.
    result = runner.invoke(cli, ["draft", "split", "block", "b3", "6"])

    assert result.exit_code == 0, result.output
    assert result.output == "Wrote b3a and b3b.\n"


def test_the_halves_of_a_split_block_are_blocks_like_any_other(
    tmp_path: Path, monkeypatch
) -> None:
    """Splitting is only worth anything if what it leaves can be quoted by its id."""
    monkeypatch.chdir(tmp_path)
    _built(TWO_QUESTIONS, tmp_path)

    result = CliRunner().invoke(cli, ["source", "show"])

    assert result.exit_code == 0, result.output
    # In the margin against the first line of each half, which is where the ids are.
    assert "b5a  10" in result.output
    assert "b5b  12" in result.output
