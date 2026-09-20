"""The draft workflow page is run as it is printed, against the fixture it is written from.

``docs/source/drafts.md`` walks one sheet from `in2lambda source add` to `in2lambda build`,
printing every command and everything it wrote. Running the page here means a command
that says something else fails the test suite, rather than a page that goes on describing
a version of in2lambda that has gone.
"""

import json
import re
import shlex
import shutil
from pathlib import Path
from typing import Any

from click.testing import CliRunner
from conftest import DRAFTS_DIR, needs_compiler

from in2lambda.main import cli

PAGE = Path(__file__).parents[1] / "docs" / "source" / "drafts.md"
"""The page, which is read rather than generated: it is prose with commands in it."""

WALKTHROUGH = DRAFTS_DIR / "walkthrough"
"""The sheet the page walks through, which `tests/test_draft.py` covers as a draft."""

DIRECTORY = "/home/you/sheet"
"""What the page prints in place of the folder the commands were run in."""

_BLOCK = re.compile(r"^```(\w+)\n(.*?)^```", re.MULTILINE | re.DOTALL)
"""One fenced block of the page, as the language it is tagged with and its content."""


def _runs(block: str) -> list[tuple[str, str]]:
    """Each command of a console block, with everything printed under it."""
    runs: list[tuple[str, list[str]]] = []
    for line in block.splitlines():
        if line.startswith("$ "):
            runs.append((line.removeprefix("$ "), []))
        else:
            runs[-1][1].append(line)
    return [(command, "\n".join(printed)) for command, printed in runs]


def _draft(tmp_path: Path) -> dict[str, Any]:
    """The draft as the commands run so far have left it."""
    return json.loads((tmp_path / "sheet.draft.json").read_text())


def _commands(block: str, tmp_path: Path) -> None:
    """Runs a console block, checking what each command prints against the page."""
    for command, printed in _runs(block):
        typed = shlex.split(command)
        if typed[0] == "cat":
            assert (tmp_path / typed[1]).read_text().rstrip("\n") == printed
            continue
        result = CliRunner().invoke(cli, typed[1:])
        assert result.exit_code == 0, result.output
        # The folder the page names, since a command prints the path it wrote to and
        # the test runs in a directory of pytest's own naming.
        said = result.output.replace(str(tmp_path.resolve()), DIRECTORY)
        assert said.rstrip("\n") == printed, command


def _quoted(block: str, tmp_path: Path) -> None:
    """Checks a piece of the draft the page quotes against the draft itself.

    Either one field, named as the draft names it, or one entry of the log.
    """
    shown = json.loads(block)
    draft = _draft(tmp_path)
    if "command" in shown:
        assert shown in draft["log"]
    else:
        (key,) = shown
        assert {key: draft["fields"][key]} == shown


@needs_compiler
def test_every_command_the_page_prints_says_what_the_page_says(
    tmp_path: Path, monkeypatch
) -> None:
    """A reader runs the page from the top, and this runs it the same way."""
    shutil.copy(WALKTHROUGH / "source.md", tmp_path / "sheet.md")
    shutil.copy(WALKTHROUGH / "spec.yaml", tmp_path / "spec.yaml")
    monkeypatch.chdir(tmp_path)
    # Who the page records every command as having been run by, which is the default a
    # command takes from the environment rather than anything the page passes.
    monkeypatch.setenv("USER", "you")
    monkeypatch.setenv("LOGNAME", "you")

    for language, block in _BLOCK.findall(PAGE.read_text()):
        if language == "bash":
            _commands(block, tmp_path)
        elif language == "json":
            _quoted(block, tmp_path)
        elif language == "markdown":
            assert block == (WALKTHROUGH / "source.md").read_text()
        elif language == "yaml":
            assert block == (WALKTHROUGH / "spec.yaml").read_text()

    # And the commands the page ran are the fixture's, so that what a reader is shown is
    # what the draft tests rebuild, export and render.
    log = [dict(entry, by="tests") for entry in _draft(tmp_path)["log"]]
    assert log == json.loads((WALKTHROUGH / "commands.json").read_text())
