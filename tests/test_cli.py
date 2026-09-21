"""What the command line does with the current and the old form."""

import os
import shutil
import subprocess
import sys

import pytest
from click.shell_completion import ShellComplete
from click.testing import CliRunner

from in2lambda.main import cli


def test_convert_writes_the_set(filters_dir: str, tmp_path) -> None:
    """`in2lambda convert` reaches the runner and produces the zipped set."""
    example = os.path.join(filters_dir, "PartsSepSol", "example.tex")

    result = CliRunner().invoke(
        cli, ["convert", example, "PartsSepSol", "-o", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "set.zip").exists()


@pytest.mark.parametrize("path", ["example.tex", "./example.tex", "ABSOLUTE"])
def test_old_form_converts_with_a_deprecation_line(
    path: str, filters_dir: str, monkeypatch, tmp_path
) -> None:
    """The old form converts the file for every form of path, and prints one line.

    A path starting with ``/`` or ``.`` used to make click print the help and exit 0,
    so every script passing a full path appeared to succeed without converting anything.
    """
    monkeypatch.setenv("COLUMNS", "200")  # So the message is not wrapped mid-sentence.
    # Run from a directory of our own, so `out` appearing there is this command's doing.
    shutil.copy(os.path.join(filters_dir, "PartsSepSol", "example.tex"), tmp_path)
    monkeypatch.chdir(tmp_path)
    if path == "ABSOLUTE":  # Only known once we're in the directory holding the file.
        path = os.path.abspath("example.tex")

    result = CliRunner().invoke(cli, [path, "PartsSepSol"])

    assert result.exit_code == 0, result.output
    assert "in2lambda FILE FILTER is the old form" in result.stderr
    assert (tmp_path / "out" / "set.zip").exists()


def test_old_form_works_when_run_as_the_installed_command(
    filters_dir: str, tmp_path
) -> None:
    """The old form converts through ``cli()``, which the installed command runs.

    CliRunner calls ``cli.main`` instead, so CliRunner does not cover this path. On
    beartype 0.18.5 the import hook left ``cli`` a plain function, and ``cli()`` ran
    ``convert``'s body whatever the arguments.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from in2lambda.main import cli; cli()",
            os.path.join(filters_dir, "PartsSepSol", "example.tex"),
            "PartsSepSol",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={**os.environ, "COLUMNS": "200"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "in2lambda FILE FILTER is the old form" in result.stderr
    assert "old form" not in result.stdout
    assert (tmp_path / "out" / "set.zip").exists()


def test_first_argument_that_is_neither_still_names_convert(
    monkeypatch, tmp_path
) -> None:
    """A first argument that is neither a subcommand nor a file is refused."""
    monkeypatch.setenv("COLUMNS", "200")  # So the message is not wrapped mid-sentence.
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["missing.tex", "PartsSepSol"])

    assert result.exit_code != 0
    assert "in2lambda convert" in result.output


def test_convert_leaves_only_what_it_writes(filters_dir: str, tmp_path) -> None:
    """Converting in an empty directory leaves the input and the output and nothing else.

    In a subprocess because importing the package is what used to leave a file behind:
    within pytest it happens once, before any test can chdir somewhere of its own.
    """
    shutil.copy(os.path.join(filters_dir, "PartsSepSol", "example.tex"), tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from in2lambda.main import cli; cli()",
            "convert",
            "example.tex",
            "PartsSepSol",
            "-o",
            "out",
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert {path.name for path in tmp_path.iterdir()} == {"example.tex", "out"}


def test_completing_the_old_form_offers_the_subcommand() -> None:
    """Completion resolves half-typed command lines, so the guard must not fire there.

    Without that exemption, `in2lambda ./questions.tex <TAB>` printed a traceback
    where the shell expected candidates.
    """
    completions = ShellComplete(
        cli, {}, "in2lambda", "_IN2LAMBDA_COMPLETE"
    ).get_completions(["./questions.tex"], "")

    assert [candidate.value for candidate in completions] == [
        "build",
        "compare",
        "convert",
        "draft",
        "render",
        "source",
        "spec",
        "validate",
    ]
