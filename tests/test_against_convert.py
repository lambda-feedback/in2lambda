"""Takes one document down both routes and compares what each makes of it.

`in2lambda convert` reads a document with a filter and writes a set. The draft workflow
freezes the same document, fills a draft's fields in from it, checks the draft over and
builds the set from the fields. Each folder in ``fixtures/against_convert`` is one
document put through both, so that a difference between the two is a test failure rather
than something a first real run finds. Where the two routes do differ today, the folder
holds a ``differs.txt`` naming each place and the ticket that would close it; the folder's
README says what the comparison folds out before looking.

The zip a draft builds is also compared with the real exports in ``fixtures/exports``, and
each draft is replayed from its log, so that one run covers what the route writes as well
as what it says.
"""

import json
import shutil
import warnings
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import (
    AGAINST_CONVERT,
    EXPORTS,
    SOURCES_DIR,
    key_paths,
    needs_compiler,
    unexported_keys,
)

import in2lambda.draft
import in2lambda.draft.report
from in2lambda.api.set import Set
from in2lambda.compare import differences, known
from in2lambda.filters import builtin_filters
from in2lambda.main import cli, runner

# Both routes compile the set and render its maths, which is what the two are being
# compared over, so a machine without the toolchain runs none of this.
pytestmark = needs_compiler

each_folder = pytest.mark.parametrize(
    "folder", AGAINST_CONVERT, ids=lambda path: path.name
)


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
        in2lambda.draft.report.validate(draft_path)
    # The checks compile the set and render its maths, which is two of the stages this
    # test is about, so a run that reported neither has not been over them.
    missing = [
        str(warning.message) for warning in said if "install" in str(warning.message)
    ]
    assert not missing, missing

    result = cli_runner.invoke(cli, ["build"])
    assert result.exit_code == 0, result.output
    return draft_path, source, layout


@each_folder
def test_the_draft_route_agrees_with_convert(
    folder: Path, tmp_path: Path, filters_dir: str, monkeypatch
) -> None:
    """Both routes make the same set of the same document, bar the folder's differs.txt."""
    monkeypatch.chdir(tmp_path)
    _, source, layout = _built(folder, tmp_path, filters_dir)

    assert differences(
        Set.from_json(str(tmp_path / "out" / "set.zip")), runner(str(source), layout)
    ) == known(folder / "differs.txt")


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


def test_a_spec_that_swaps_part_and_solution_is_caught(
    tmp_path: Path, monkeypatch
) -> None:
    """A draft that says something else about a question fails, naming that question.

    Every folder agrees with convert save where its ``differs.txt`` says, so a
    comparison that could not tell them from a draft built wrongly would pass them as
    well. The spec here reads each solution as the part and each part as the solution.
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
        assert (
            differences(
                Set.from_json(str(tmp_path / "out" / "set.zip")),
                runner(str(source), "PartsOneSol"),
            )
            == []
        )
