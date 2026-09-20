"""Running a spec of selectors over a frozen source.

Each folder in ``fixtures/specs`` is a document, the spec to run over it, the fields it
should fill in and the blocks it should leave out, so covering another kind of document
means adding a folder rather than a test. The rest is what the command line does with a
spec it cannot read - a typo in a selector, a layout nothing has, a file edited since it
was run - which is not something a fixture can say.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import SPECS, SPECS_DIR

from in2lambda.main import cli

WORKED_EXAMPLE = SPECS_DIR / "parts_sep_sol"
"""The case the tests below happen to use; what they check holds for any of them."""


def _frozen(folder: Path, tmp_path: Path) -> CliRunner:
    """A folder's document and its spec, copied into `tmp_path` with the source frozen."""
    shutil.copytree(folder, tmp_path, dirs_exist_ok=True)
    runner = CliRunner()
    assert runner.invoke(cli, ["source", "add", "source.md"]).exit_code == 0
    return runner


@pytest.mark.parametrize("folder", SPECS, ids=lambda path: path.name)
def test_a_spec_fills_in_the_fields_beside_it_and_replays(
    folder: Path, tmp_path: Path, monkeypatch
) -> None:
    """What a spec makes of a document, and that its log rebuilds the same draft."""
    monkeypatch.chdir(tmp_path)
    runner = _frozen(folder, tmp_path)

    result = runner.invoke(cli, ["spec", "run", "spec.yaml", "--by", "tests"])

    assert result.exit_code == 0, result.output
    draft_path = tmp_path / "draft.json"
    draft = json.loads(draft_path.read_text())
    assert draft["fields"] == json.loads((folder / "expected.json").read_text())

    reported = [
        line.split()[0] for line in result.output.splitlines() if "no field" in line
    ]
    assert reported == (folder / "uncovered.txt").read_text().split()

    # The spec is named and hashed in the log, so a replay runs the one that ran.
    spec = (tmp_path / "spec.yaml").read_bytes()
    assert draft["log"] == [
        {
            "command": "spec run",
            "args": {
                "spec": "spec.yaml",
                "hash": f"sha256:{hashlib.sha256(spec).hexdigest()}",
            },
            "by": "tests",
        }
    ]

    written = draft_path.read_bytes()
    replay = runner.invoke(cli, ["draft", "replay"])

    assert replay.exit_code == 0, replay.output
    assert draft_path.read_bytes() == written


def test_a_replay_is_refused_once_the_spec_has_changed(
    tmp_path: Path, monkeypatch
) -> None:
    """The fields came from the spec as it was, so a replay of a new one proves nothing."""
    monkeypatch.setenv("COLUMNS", "200")  # So the message is not wrapped mid-sentence.
    monkeypatch.chdir(tmp_path)
    runner = _frozen(WORKED_EXAMPLE, tmp_path)
    assert runner.invoke(cli, ["spec", "run", "spec.yaml"]).exit_code == 0
    draft_path = tmp_path / "draft.json"
    written = draft_path.read_bytes()

    spec = tmp_path / "spec.yaml"
    spec.write_text(spec.read_text().replace("PartsSepSol", "PartsOneSol"))
    result = runner.invoke(cli, ["draft", "replay"])

    assert result.exit_code != 0
    assert "spec.yaml has changed" in result.output
    assert draft_path.read_bytes() == written


def test_a_replay_is_refused_once_the_spec_has_gone(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft names the spec that filled it in, and someone may well have moved it."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    runner = _frozen(WORKED_EXAMPLE, tmp_path)
    assert runner.invoke(cli, ["spec", "run", "spec.yaml"]).exit_code == 0
    (tmp_path / "spec.yaml").unlink()

    result = runner.invoke(cli, ["draft", "replay"])

    assert result.exit_code != 0
    assert "spec.yaml" in result.output


@pytest.mark.parametrize(
    ("spec", "line", "named"),
    [
        ("question: Header\n  layout: PartsOneSol\n", "line 2", "not YAML"),
        ("question: Header\nlayout: Sausage\n", "line 2", "Sausage"),
        ("question: Sausage\nlayout: PartsOneSol\n", "line 1", "pandoc element"),
        ("question: Header colour=blue\nlayout: PartsOneSol\n", "line 1", "colour"),
        ("quesiton: Header\nlayout: PartsOneSol\n", "line 1", "quesiton"),
    ],
    ids=["not yaml", "unknown layout", "unknown type", "unknown attribute", "typo"],
)
def test_a_spec_that_cannot_be_read_says_which_line_to_look_at(
    spec: str, line: str, named: str, tmp_path: Path, monkeypatch
) -> None:
    """A spec is written by hand, so a mistake in one is a message, not a traceback."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    runner = _frozen(WORKED_EXAMPLE, tmp_path)
    written = (tmp_path / "draft.json").read_bytes()
    (tmp_path / "spec.yaml").write_text(spec)

    result = runner.invoke(cli, ["spec", "run", "spec.yaml"])

    assert result.exit_code != 0
    assert named in result.output
    assert line in result.output
    assert isinstance(result.exception, SystemExit)
    # Nothing is half written: the draft is as it was before the spec was run.
    assert (tmp_path / "draft.json").read_bytes() == written


def test_a_spec_saved_as_utf_16_is_read_like_any_other(
    tmp_path: Path, monkeypatch
) -> None:
    """A spec is written in whatever the editor saves in, and YAML reads the BOM."""
    monkeypatch.chdir(tmp_path)
    runner = _frozen(WORKED_EXAMPLE, tmp_path)
    spec = tmp_path / "spec.yaml"
    spec.write_bytes(spec.read_text().encode("utf-16"))

    result = runner.invoke(cli, ["spec", "run", "spec.yaml", "--by", "tests"])

    assert result.exit_code == 0, result.output
    fields = json.loads((tmp_path / "draft.json").read_text())["fields"]
    assert fields == json.loads((WORKED_EXAMPLE / "expected.json").read_text())


def test_a_spec_in_an_encoding_yaml_cannot_read_is_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """A spec saved as cp1252 is something to say so about, not a decoding traceback."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    runner = _frozen(WORKED_EXAMPLE, tmp_path)
    written = (tmp_path / "draft.json").read_bytes()
    (tmp_path / "spec.yaml").write_bytes(
        "question: Header\nstrip: ['^Solución ']\nlayout: PartsOneSol\n".encode(
            "cp1252"
        )
    )

    result = runner.invoke(cli, ["spec", "run", "spec.yaml"])

    assert result.exit_code != 0
    assert "not YAML" in result.output
    assert isinstance(result.exception, SystemExit)
    assert (tmp_path / "draft.json").read_bytes() == written


def test_running_a_spec_without_pyyaml_says_what_to_install(
    tmp_path: Path, monkeypatch
) -> None:
    """Reading a spec needs pyyaml, which only the convert extra installs."""
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.chdir(tmp_path)
    runner = _frozen(WORKED_EXAMPLE, tmp_path)
    monkeypatch.setitem(sys.modules, "yaml", None)

    result = runner.invoke(cli, ["spec", "run", "spec.yaml"])

    assert result.exit_code != 0
    assert "pyyaml" in result.output
    assert "pip install 'in2lambda[convert]'" in result.output
    assert isinstance(result.exception, SystemExit)
