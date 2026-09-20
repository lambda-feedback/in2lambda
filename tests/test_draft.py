"""Building a draft by commands, and rebuilding it from the ones it recorded.

Each folder in ``fixtures/drafts`` is a document, the commands to run against its draft
and the fields they should write, so covering another command means adding a folder
rather than a test. Each is also what `in2lambda build` and `in2lambda render` make of
it: one whose ``report.json`` holds a finding at level error is refused, and one holding
only warnings - a question or part nothing answers - is exported with them said. The
remainder is
what the command line does when a replay cannot be trusted - a source that has moved on,
a log naming a command nothing has, a draft edited by hand - which is not something a
fixture can say.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from conftest import DRAFTS, DRAFTS_DIR, frozen_sources, needs_compiler

import in2lambda.draft
import in2lambda.draft.report
from in2lambda.api.set import Set
from in2lambda.json_convert.json_convert import _IMAGE
from in2lambda.main import cli
from in2lambda.validation import pdf

QUESTION = re.compile(r"q(\d+)\.text")
"""A question's text among a folder's fields, which is one question of the export."""

PART = re.compile(r"q(\d+)\.p(\d+)\.text")
"""A part's text, which is one part of the question it is numbered under."""

MARK_IGNORE = DRAFTS_DIR / "mark_ignore"
"""The case the tests below happen to use; what they check holds for any of them."""

TWO_QUESTIONS = DRAFTS_DIR / "two_questions"
"""The one with questions written into it, which is what refusing a second one needs."""

FIGURE = DRAFTS_DIR / "figure_in_a_question"
"""The one whose fields refer to an image file, which the export has to carry."""

SOLUTIONS = DRAFTS_DIR / "solutions_in_a_second_source"
"""The one written as two documents, for what a command naming the second one does."""

DEGREES = DRAFTS_DIR / "degrees"
"""The one whose report comes from the set the draft describes rather than the draft."""

QUESTIONS_ONLY = DRAFTS_DIR / "questions_only"
"""A second sheet to put beside another, for the folder holding more than one."""


def _built(folder: Path, tmp_path: Path) -> Path:
    """A folder's documents, frozen in `tmp_path` with its commands applied and checked."""
    shutil.copytree(folder, tmp_path, dirs_exist_ok=True)
    # A folder holding a solutions.md is a sheet written as two documents, and freezes
    # the solutions as its second source; everything of it is then named 2/b3, 2/s14.
    sources = frozen_sources(tmp_path)
    assert CliRunner().invoke(cli, ["source", "add", *sources]).exit_code == 0
    draft_path = tmp_path / "source.draft.json"
    for entry in json.loads((folder / "commands.json").read_text()):
        in2lambda.draft.execute(entry, draft_path)
    # Checked as well as built, so that what a folder's commands leave for the checks to
    # find is fixture data like the fields they write are.
    in2lambda.draft.report.validate(draft_path)
    return draft_path


def _expected_parts(fields: dict[str, Any], number: int) -> int:
    """How many parts a question's fields describe, counted from the fields themselves.

    One per ``qN.pM.text``, and one more where ``qN.solution`` is written beside a
    solution for every part there is: nothing is left for it to answer, so it is a part
    of its own, as `in2lambda convert` writes one. A question with no parts written for
    it at all is one empty part, since a question exported holding none carries the
    template's placeholder wording instead.
    """
    written = [
        int(found[2])
        for key in fields
        if (found := PART.fullmatch(key)) and int(found[1]) == number
    ]
    answered = all(f"q{number}.p{part}.solution" in fields for part in written)
    parts = len(written) + (answered and f"q{number}.solution" in fields)
    return parts or 1


def _as_exported(value: str) -> str:
    """A field's markdown as the export writes it out.

    The same wording, save that an image reference names the file as it sits in the
    export's ``media/``, which is by its own name where no two figures beside the draft
    share one.
    """
    return _IMAGE.sub(
        lambda ref: ref[0][: ref.start(1) - ref.start()] + Path(ref[1]).name + ")",
        value,
    )


def _reported(folder: Path) -> list[dict[str, Any]]:
    """What the checks should find in a folder's draft; nothing, where it says none."""
    report = folder / "report.json"
    return json.loads(report.read_text()) if report.is_file() else []


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
    assert draft["report"] == _reported(folder)

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
        (
            {
                "command": "field replace",
                "args": {"field": "b1.ignore", "old": "a"},
                "by": "tests",
            },
            "new",
        ),
        (
            {
                "command": "field replace",
                "args": {
                    "field": "b1.ignore",
                    "old": "a",
                    "new": "b",
                    "regex": "yes",
                },
                "by": "tests",
            },
            "true or false",
        ),
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
        "no new argument",
        "a regex that is neither true nor false",
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
        ("fields", {"b1.ignore": {"ranges": [[1, 1]], "layer": 3}}),
    ],
    ids=[
        "log",
        "fields",
        "a field that is a number",
        "ranges that are not a list",
        "a range that is not a pair",
        "a field with no value",
    ],
)
@pytest.mark.parametrize(
    "arguments",
    [["draft", "replay"], ["draft", "mark", "ignore", "b2"], ["validate"]],
    ids=["replay", "mark", "validate"],
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


def test_the_refusal_names_the_lines_that_are_in_the_way(
    tmp_path: Path, monkeypatch
) -> None:
    """A field edited by hand can be quoted from several ranges, only one of them clashing."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    draft = json.loads(draft_path.read_text())
    # The maths is part of the heading's block as far as this draft is concerned, which
    # no command would write but an editor might.
    draft["fields"]["b1.ignore"]["ranges"] = [[1, 1], [9, 10]]
    draft_path.write_text(json.dumps(draft))

    result = CliRunner().invoke(cli, ["draft", "question", "add", "--text", "s9:10"])

    assert result.exit_code != 0
    # Lines 1-1 are free, so naming them would send whoever reads this to the wrong end.
    assert "Lines 9-10" in result.output


@pytest.mark.parametrize(
    ("arguments", "named"),
    [
        (["draft", "question", "add", "--text", "s99:100"], "s99:100"),
        (["draft", "question", "add", "--text", "2/s1:2"], "2/s1:2"),
        (["draft", "question", "add", "--text", "9/b1"], "9/b1"),
        (["draft", "question", "add", "--text", "s6:5"], "s6:5"),
        (["draft", "question", "add", "--text", "sixteen"], "sixteen"),
        (["draft", "question", "add", "--text", "s8", "--literal", "Words."], "both"),
        (["draft", "question", "add"], "neither"),
        (["draft", "part", "add", "q9", "--text", "s8"], "q9"),
        (["draft", "split", "block", "b3", "5"], "b3 is lines 5-6"),
        (["draft", "split", "block", "b3", "7"], "b3 is lines 5-6"),
        # q1.text has a $d$ and a $v$ in it, so a $ names four places and none of them.
        (["draft", "field", "replace", "q1.text", "$", "X"], "occurs 4 times"),
        (["draft", "field", "replace", "q1.text", "steam", "water"], "occurs 0 times"),
        (["draft", "field", "replace", "q9.text", "a", "b"], "q9.text"),
        (["draft", "field", "replace", "b1.ignore", "a", "b"], "b1.ignore"),
        (["draft", "field", "set", "q9.text", "--text", "s3"], "q9.text"),
        (["draft", "field", "set", "b1.ignore", "--text", "s3"], "b1.ignore"),
        # Line 16 is where q1's solution came from, so it is not also q2's text.
        (["draft", "field", "set", "q2.text", "--text", "s16"], "q1.solution"),
        (
            ["draft", "field", "replace", "q1.text", "(", "X", "--regex"],
            "not a regular expression",
        ),
    ],
    ids=[
        "lines the source has not got",
        "lines of a source the draft has not got",
        "a block of a source it has not got",
        "a range that runs backwards",
        "a text that is no kind of address",
        "a text and a literal",
        "no text and no literal",
        "a question nothing has written",
        "a split at the line the block starts on",
        "a split past the line it ends on",
        "wording the field says more than once",
        "wording the field does not say",
        "a field nothing has written",
        "a field that is not text",
        "a field set naming a field nothing has written",
        "a field set naming a field that is not text",
        "a field set quoting lines another field was taken from",
        "a regex that is not one",
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

    # And a replacement names the field it changed, which it leaves quoting the same
    # lines as before, said to be edited, and by whoever replaced the wording.
    result = runner.invoke(
        cli,
        ["draft", "field", "replace", "q1.solution", "d^2", "d^{2}", "--by", "ocr"],
    )

    assert result.exit_code == 0, result.output
    assert result.output == "Wrote q1.solution.\n"
    draft = json.loads(draft_path.read_text())
    assert draft["fields"]["q1.solution"] == {
        "value": "The flow rate is $Q = \\pi d^{2} v / 4$.",
        "layer": 3,
        "ranges": [[16, 16]],
        "edited": True,
        "by": "ocr",
    }
    # --regex is an option, so a command nobody passed it to logs no argument for it.
    assert "regex" not in draft["log"][-1]["args"]

    # And a field set names the field it quoted into, which holds the lines it names and
    # nothing of the range it named before: q1.text was lines 5-6 and is now line 5.
    result = runner.invoke(
        cli, ["draft", "field", "set", "q1.text", "--text", "s5", "--by", "ocr"]
    )

    assert result.exit_code == 0, result.output
    assert result.output == "Wrote q1.text.\n"
    assert json.loads(draft_path.read_text())["fields"]["q1.text"] == {
        "value": "Water flows through a horizontal pipe of diameter $d$ at speed $v$.",
        "layer": 3,
        "ranges": [[5, 5]],
        "edited": False,
        "by": "ocr",
    }


def test_a_field_is_quoted_from_a_later_source_by_its_number(
    tmp_path: Path, monkeypatch
) -> None:
    """A block or a range of the solutions is named as the sheet's is, with its number."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    shutil.copytree(SOLUTIONS, tmp_path, dirs_exist_ok=True)
    runner = CliRunner()
    assert (
        runner.invoke(cli, ["source", "add", "source.md", "solutions.md"]).exit_code
        == 0
    )

    # Each question out of the sheet and each solution out of the document beside it,
    # once as the block it is and once as the lines it spans.
    for arguments in (
        ["draft", "question", "add", "--text", "b2"],
        ["draft", "part", "add", "q1", "--text", "b3"],
        ["draft", "question", "solution", "q1", "--text", "2/b3"],
        ["draft", "question", "add", "--text", "s9"],
        ["draft", "question", "solution", "q2", "--text", "2/s11"],
    ):
        result = runner.invoke(cli, arguments)
        assert result.exit_code == 0, result.output

    fields = json.loads((tmp_path / "source.draft.json").read_text())["fields"]
    assert fields["q1.solution"]["value"] == "The load is $F = pA$."
    assert fields["q2.solution"]["value"] == "Solution: The drag is $\\tau A$."
    # Line 5 of the sheet is q1's part and line 5 of the solutions is what answers it:
    # the same numbers, and no clash, because each field says which source it is of.
    assert fields["q1.p1.text"]["ranges"] == fields["q1.solution"]["ranges"] == [[5, 5]]
    assert "source" not in fields["q1.p1.text"]
    assert fields["q1.solution"]["source"] == 2

    # A number in front of an address that carries one already is no address at all, and
    # is refused as what was given. Read as source 1's own 2/b6 it would find the block
    # and then quote line 11 of the sheet, which is nine lines long - a field holding
    # nothing, from a document nobody named, that a replay would reproduce faithfully.
    result = runner.invoke(cli, ["draft", "question", "add", "--text", "1/2/b6"])
    assert result.exit_code != 0, result.output
    assert "1/2/b6" in result.output


def test_a_draft_edited_into_an_overlap_or_a_gap_is_reported(
    tmp_path: Path, monkeypatch
) -> None:
    """Neither can be made by a command, so a hand-edited draft is the only way to one."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)
    draft = json.loads(draft_path.read_text())
    # Renumbering the second question leaves nothing numbered 2, and giving the first
    # question's part the lines the question came from claims those lines twice.
    for key in ("q2.text", "q2.p1.text", "q2.solution"):
        draft["fields"][key.replace("q2", "q3")] = draft["fields"].pop(key)
    draft["fields"]["q1.p1.text"]["ranges"] = [[5, 6]]
    draft_path.write_text(json.dumps(draft))

    result = CliRunner().invoke(cli, ["validate"])

    assert result.exit_code == 0, result.output
    report = json.loads(draft_path.read_text())["report"]
    assert [(finding["check"], finding["field"]) for finding in report] == [
        ("overlap", "q1.p1.text"),
        ("gap", "q2.text"),
    ]
    # Both are the draft contradicting its own source, so neither is one to export over.
    assert [finding["level"] for finding in report] == ["error", "error"]
    # Both sides of the overlap, so that either field can be looked at without the draft.
    assert "q1.text" in report[0]["message"]
    assert result.output == f"{report[0]['message']}\n{report[1]['message']}\n"


def test_a_clean_draft_is_reported_as_having_nothing_wrong_with_it(
    tmp_path: Path, monkeypatch
) -> None:
    """A report of nothing is still an answer, and is said rather than printed empty."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)

    result = CliRunner().invoke(cli, ["validate"])

    assert result.exit_code == 0, result.output
    assert result.output == "Nothing to report.\n"
    assert json.loads(draft_path.read_text())["report"] == []


@needs_compiler
def test_validate_reports_what_the_pdf_generator_cannot_compile(
    tmp_path: Path, monkeypatch
) -> None:
    """The set a draft describes is compiled as well as read, against the field it is in.

    Only a compile says this: the fixtures cover what is found by reading the markdown,
    and nothing there would tell a run with the toolchain installed from one without.
    """
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)
    replaced = CliRunner().invoke(
        cli,
        [
            "draft",
            "field",
            "replace",
            "q1.solution",
            "$Q = \\pi d^2 v / 4$",
            "$x = \\nosuchcommand$",
        ],
    )
    assert replaced.exit_code == 0, replaced.output

    report = in2lambda.draft.report.validate(draft_path)

    refused = [
        finding
        for finding in report
        if "the PDF generator cannot compile this" in finding["message"]
    ]
    assert [finding["field"] for finding in refused] == ["q1.solution"]
    # Named as a field of the draft, since that is what `field replace` takes, rather
    # than as the part of the export the solution ended up answering.
    assert refused[0]["message"].startswith("q1.solution (lines 16-16): ")


@needs_compiler
def test_a_replay_without_the_toolchain_keeps_what_validate_found_with_it(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft is replayed where it is read, which need not be where it was checked.

    Our own Docker image installs pandoc and no xelatex, so a report written here and
    replayed there would come back a finding short if the replay ran the set checks
    again - and the draft, untouched, would be called hand-edited.
    """
    monkeypatch.chdir(tmp_path)
    draft_path = _built(TWO_QUESTIONS, tmp_path)
    replaced = CliRunner().invoke(
        cli,
        [
            "draft",
            "field",
            "replace",
            "q1.solution",
            "$Q = \\pi d^2 v / 4$",
            "$x = \\nosuchcommand$",
        ],
    )
    assert replaced.exit_code == 0, replaced.output
    assert any(
        "the PDF generator cannot compile this" in finding["message"]
        for finding in in2lambda.draft.report.validate(draft_path)
    )

    monkeypatch.setattr(pdf, "missing_tools", lambda: ["xelatex (how to install it)"])
    result = CliRunner().invoke(cli, ["draft", "replay"])

    assert result.exit_code == 0, result.output


def test_validate_says_what_to_install_rather_than_reporting_the_compile(
    tmp_path: Path, monkeypatch
) -> None:
    """The toolchain is optional here as it is everywhere else: the rest still runs."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(DEGREES, tmp_path)
    monkeypatch.setattr(pdf, "missing_tools", lambda: ["pandoc (how to install it)"])

    with pytest.warns(UserWarning, match="pandoc"):
        report = in2lambda.draft.report.validate(draft_path)

    # What reading the markdown found, and nothing about the compile that was not run:
    # the set is not compiled at all, so it has nothing to say about it either way.
    assert [finding["field"] for finding in report] == ["q1.text", "q1.solution"]
    assert not any("compile" in finding["message"] for finding in report)


def test_a_command_run_after_a_report_leaves_none_behind(
    tmp_path: Path, monkeypatch
) -> None:
    """A report describes the draft it was run against, and that draft has changed."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    assert json.loads(draft_path.read_text())["report"]

    result = CliRunner().invoke(cli, ["draft", "mark", "ignore", "b2"])

    assert result.exit_code == 0, result.output
    assert "report" not in json.loads(draft_path.read_text())


def test_freezing_another_source_leaves_no_report_behind(
    tmp_path: Path, monkeypatch
) -> None:
    """A report says nothing about a document frozen after it was written."""
    monkeypatch.chdir(tmp_path)
    draft_path = _built(MARK_IGNORE, tmp_path)
    assert json.loads(draft_path.read_text())["report"]
    (tmp_path / "solutions.md").write_text("# Solutions\n\n1. The load is $F = pA$.\n")
    runner = CliRunner()

    assert (
        runner.invoke(
            cli, ["source", "add", "solutions.md", "--draft", "source.md"]
        ).exit_code
        == 0
    )

    # Every block of the new source is in no field, so a report written before it was
    # frozen is not a report of this draft - which a replay, running the checks again
    # over what it rebuilt, is what catches.
    assert "report" not in json.loads(draft_path.read_text())
    assert runner.invoke(cli, ["draft", "replay"]).exit_code == 0

    # Naming a file the draft has got already does leave it: nothing has changed, so
    # what the checks found still holds.
    in2lambda.draft.report.validate(draft_path)
    assert (
        runner.invoke(
            cli, ["source", "add", "solutions.md", "--draft", "source.md"]
        ).exit_code
        == 0
    )
    assert json.loads(draft_path.read_text())["report"]


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


def test_build_refuses_a_draft_that_has_not_been_validated(
    tmp_path: Path, monkeypatch
) -> None:
    """Every command that changes a draft drops its report, so this is every draft."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    shutil.copytree(TWO_QUESTIONS, tmp_path, dirs_exist_ok=True)
    assert CliRunner().invoke(cli, ["source", "add", "source.md"]).exit_code == 0
    for entry in json.loads((TWO_QUESTIONS / "commands.json").read_text()):
        in2lambda.draft.execute(entry, tmp_path / "source.draft.json")

    result = CliRunner().invoke(cli, ["build"])

    assert result.exit_code != 0
    assert "in2lambda validate" in result.output
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("folder", DRAFTS, ids=lambda path: path.name)
def test_build_follows_the_report(folder: Path, tmp_path: Path, monkeypatch) -> None:
    """A draft is exported once the checks have found no error in it.

    A warning does not stop it: a sheet whose solutions are in another file or nowhere at
    all is a sheet to export, and is exported with what was found said beside it.
    """
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    _built(folder, tmp_path)
    fields = json.loads((folder / "expected.json").read_text())
    report = _reported(folder)

    result = CliRunner().invoke(cli, ["build"])

    if refusing := [finding for finding in report if finding["level"] == "error"]:
        assert result.exit_code != 0, result.output
        # Every error, so that what is left to do can be read off the refusal itself.
        for finding in refusing:
            assert finding["message"] in result.output
        assert not (tmp_path / "out").exists()
        return

    assert result.exit_code == 0, result.output
    # And each warning said, since the set was written over it rather than without it.
    for finding in report:
        assert finding["message"] in result.output
    exported = tmp_path / "out" / "set.zip"
    assert exported.is_file()

    questions = Set.from_json(str(exported)).questions
    assert len(questions) == len([key for key in fields if QUESTION.fullmatch(key)])
    for number, question in enumerate(questions, start=1):
        assert question.main_text == _as_exported(fields[f"q{number}.text"]["value"])
        # Counted from the fields rather than read off the question, since a loop over
        # parts that were dropped runs no assertions and passes saying nothing.
        assert len(question.parts) == _expected_parts(fields, number)
        for index, part in enumerate(question.parts, start=1):
            if f"q{number}.p{index}.text" not in fields:
                # The question's own solution, written where every part is answered
                # already: last, and holding nothing but that solution. Or, where the
                # question has no solution either, the empty part a question with no
                # parts written for it exports as.
                assert part.text == ""
                solution = fields.get(f"q{number}.solution")
                assert part.worked_solution == (
                    _as_exported(solution["value"]) if solution else ""
                )
                continue
            assert part.text == _as_exported(
                fields[f"q{number}.p{index}.text"]["value"]
            )
            # A part's own solution, or the question's where it has none of its own.
            solution = fields.get(
                f"q{number}.p{index}.solution", fields.get(f"q{number}.solution")
            )
            assert part.worked_solution == (
                _as_exported(solution["value"]) if solution else ""
            )

    # Every image a field refers to travels with the set under media/, named as the
    # written JSON refers to it, since that name is the only way Lambda Feedback finds
    # one; the set's folder is asked rather than the loaded questions, because reading an
    # export back attributes an image to a question by the platform's own naming of the
    # file, which a draft's images do not follow.
    written = tmp_path / "out" / "set"
    references = {
        reference
        for file in written.glob("question_*.json")
        for reference in _IMAGE.findall(file.read_text())
    }
    assert all(
        (written / "media" / reference).is_file() for reference in references
    ), references
    # One file per file the fields point at, whatever path each was written as.
    assert len(list((written / "media").glob("*"))) == len(
        {
            (tmp_path / reference).resolve()
            for field in fields.values()
            if isinstance(field["value"], str)
            for reference in _IMAGE.findall(field["value"])
        }
    )


def test_two_sources_in_one_folder_each_have_a_draft_of_their_own(
    tmp_path: Path, monkeypatch
) -> None:
    """A folder is a course's worth of sheets, and each is worked on without the others.

    Neither a fixture folder nor `_built` can say this: both are one source per folder,
    and what is being checked is that the second sheet does not land on the first.
    """
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    # Named by its source for one sheet and by its draft for the other, since --draft
    # takes either and both are what a folder of sheets gets worked on with.
    sheets = {"a": (QUESTIONS_ONLY, "a.md"), "b": (TWO_QUESTIONS, "b.draft.json")}
    for name, (folder, _) in sheets.items():
        shutil.copy(folder / "source.md", tmp_path / f"{name}.md")
        assert runner.invoke(cli, ["source", "add", f"{name}.md"]).exit_code == 0

    drafts = {name: tmp_path / f"{name}.draft.json" for name in sheets}
    assert all(path.is_file() for path in drafts.values())

    for name, (folder, named) in sheets.items():
        untouched = {
            path: path.read_bytes() for other, path in drafts.items() if other != name
        }
        for entry in json.loads((folder / "commands.json").read_text()):
            in2lambda.draft.execute(entry, drafts[name])
        validated = runner.invoke(cli, ["validate", "--draft", named])
        assert validated.exit_code == 0, validated.output
        built = runner.invoke(cli, ["build", "--draft", named, "--out", name])
        assert built.exit_code == 0, built.output

        # Every other draft in the folder is the file it was, byte for byte, and the
        # set written is the one this draft describes rather than whichever was last.
        assert {path: path.read_bytes() for path in untouched} == untouched
        fields = json.loads((folder / "expected.json").read_text())
        questions = Set.from_json(str(tmp_path / name / "set.zip")).questions
        assert len(questions) == len([key for key in fields if QUESTION.fullmatch(key)])
        for number, question in enumerate(questions, start=1):
            assert question.main_text == fields[f"q{number}.text"]["value"]

    # And with two of them there, a command that was not told which is refused rather
    # than acting on whichever sorts first.
    result = runner.invoke(cli, ["validate"])

    assert result.exit_code != 0
    assert "a.draft.json" in result.output
    assert "b.draft.json" in result.output
    assert "--draft" in result.output


def test_build_refuses_a_field_naming_an_image_that_is_not_there(
    tmp_path: Path, monkeypatch
) -> None:
    """The checks read the draft and not the folder, so a clean one can still say this.

    Exporting it anyway would upload a question whose figure is a broken image, since
    the file the markdown names is what the export carries under media/.
    """
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    _built(FIGURE, tmp_path)
    (tmp_path / "figure.png").unlink()

    result = CliRunner().invoke(cli, ["build"])

    assert result.exit_code != 0
    assert "figure.png" in result.output
    assert not (tmp_path / "out").exists()


@needs_compiler
def test_render_leaves_out_a_figure_that_is_not_there(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft is rendered to look at, and a figure yet to be found is one such fault.

    The compiler drops the reference and typesets the rest, which is what `build`
    refuses to upload and what a reviewer wants to see.
    """
    monkeypatch.chdir(tmp_path)
    _built(FIGURE, tmp_path)
    (tmp_path / "figure.png").unlink()

    result = CliRunner().invoke(cli, ["render"])

    assert result.exit_code == 0, result.output
    written = sorted((tmp_path / "out").glob("*.pdf"))
    assert len(written) == 1
    assert written[0].stat().st_size


@needs_compiler
def test_render_writes_the_questions_beside_one_tex_cannot_finish(
    tmp_path: Path, monkeypatch
) -> None:
    """Maths a brace is missing out of makes TeX give up where it stands.

    That is one question of the draft unrendered, and it is said as such: the rest is
    still written out, since a draft whose faults are being fixed is exactly the one
    somebody is looking at.
    """
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    _built(TWO_QUESTIONS, tmp_path)
    replaced = CliRunner().invoke(
        cli,
        [
            "draft",
            "field",
            "replace",
            "q1.solution",
            "$Q = \\pi d^2 v / 4$",
            "$\\frac{1$",
        ],
    )
    assert replaced.exit_code == 0, replaced.output

    result = CliRunner().invoke(cli, ["render"])

    assert result.exit_code == 0, result.output
    # The second question, which has nothing wrong with it.
    written = sorted((tmp_path / "out").glob("*.pdf"))
    assert len(written) == 1
    assert written[0].stat().st_size
    # Why the first one is not there, rather than only that xelatex wrote no PDF: the
    # log's own account of it is all there is when it stopped before reaching a field.
    assert "File ended while scanning use of \\frac" in result.output


@needs_compiler
@pytest.mark.parametrize("folder", DRAFTS, ids=lambda path: path.name)
def test_render_writes_one_pdf_per_question(
    folder: Path, tmp_path: Path, monkeypatch
) -> None:
    """Rendering is for looking at a draft, so a draft with a report renders too."""
    monkeypatch.chdir(tmp_path)
    _built(folder, tmp_path)
    fields = json.loads((folder / "expected.json").read_text())

    result = CliRunner().invoke(cli, ["render"])

    assert result.exit_code == 0, result.output
    written = sorted((tmp_path / "out").glob("*.pdf"))
    assert len(written) == len([key for key in fields if QUESTION.fullmatch(key)])
    assert all(pdf.stat().st_size for pdf in written)


def test_render_says_what_to_install_without_the_compiler(
    tmp_path: Path, monkeypatch
) -> None:
    """The PDF generator's toolchain is optional, as it is everywhere else here."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    _built(TWO_QUESTIONS, tmp_path)
    which = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda command: None if command == "xelatex" else which(command),
    )

    result = CliRunner().invoke(cli, ["render"])

    assert result.exit_code != 0
    assert "texlive-xetex" in result.output
    assert not (tmp_path / "out").exists()


def test_render_says_which_tool_never_finished(tmp_path: Path, monkeypatch) -> None:
    """A set can be written that makes TeX loop, and waiting is not what happens then.

    The toolchain is stood in for rather than run, so that this says what the command
    does with a timeout wherever it is run, not only where a compiler is installed.
    """

    def never_finishes(command: list[str], **_: Any) -> None:
        raise subprocess.TimeoutExpired(command, pdf._TIMEOUT)

    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    _built(TWO_QUESTIONS, tmp_path)
    monkeypatch.setattr(shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(subprocess, "run", never_finishes)

    result = CliRunner().invoke(cli, ["render"])

    assert result.exit_code != 0
    # The line a reader can act on, rather than the traceback out of subprocess.
    assert "pandoc did not finish" in result.output
    assert not isinstance(result.exception, subprocess.TimeoutExpired)
