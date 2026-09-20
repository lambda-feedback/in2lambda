"""What the command line does with the current and the pre-2.0 form."""

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
def test_old_form_fails_and_names_convert(
    path: str, filters_dir: str, monkeypatch, tmp_path
) -> None:
    """The pre-2.0 form errors out whatever the file path looks like.

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

    assert result.exit_code != 0
    assert "in2lambda convert" in result.output
    assert not (tmp_path / "out").exists()


def test_old_form_fails_when_run_as_the_installed_command(
    filters_dir: str, tmp_path
) -> None:
    """The same holds for ``cli()``, which is what the installed command runs.

    CliRunner calls ``cli.main`` instead, so it cannot see this path: on beartype
    0.18.5 the import hook left ``cli`` a plain function, and ``cli()`` ran
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

    assert result.returncode != 0
    assert "in2lambda convert" in result.stdout + result.stderr
    assert not (tmp_path / "out").exists()


def test_completing_the_old_form_offers_the_subcommand() -> None:
    """Completion resolves half-typed command lines, so the guard must not fire there.

    Without that exemption, `in2lambda ./questions.tex <TAB>` printed a traceback
    where the shell expected candidates.
    """
    completions = ShellComplete(
        cli, {}, "in2lambda", "_IN2LAMBDA_COMPLETE"
    ).get_completions(["./questions.tex"], "")

    assert [candidate.value for candidate in completions] == [
        "convert",
        "draft",
        "source",
    ]
