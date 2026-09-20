"""What the command line does with the current and the pre-2.0 form."""

import os
import subprocess
import sys

import pytest
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
    monkeypatch.chdir(os.path.join(filters_dir, "PartsSepSol"))
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

    CliRunner calls ``cli.main`` instead, so it cannot see this path: beartype's
    import hook broke it below 0.18 by sending ``cli()`` to the first subcommand.
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
