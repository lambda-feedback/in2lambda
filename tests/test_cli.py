"""Tests for the ``in2lambda`` command-line interface (the ``convert`` subcommand)."""

import os

from click.testing import CliRunner

from in2lambda.main import cli


def test_bare_invocation_shows_usage() -> None:
    result = CliRunner().invoke(cli, [])
    assert "Usage:" in result.output
    assert "convert" in result.output


def test_help_lists_the_convert_command() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "convert" in result.output


def test_convert_writes_output_files(filters_dir: str, tmp_path) -> None:
    example = os.path.join(filters_dir, "PartsSepSol", "example.tex")
    out_dir = tmp_path / "out"

    result = CliRunner().invoke(
        cli, ["convert", example, "PartsSepSol", "-o", str(out_dir)]
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "set").is_dir()
    assert (out_dir / "set.zip").is_file()


def test_convert_accepts_case_insensitive_filter_and_markdown(
    filters_dir: str, tmp_path
) -> None:
    example = os.path.join(filters_dir, "Markdown", "example.md")
    out_dir = tmp_path / "out"

    result = CliRunner().invoke(
        cli, ["convert", example, "markdown", "-o", str(out_dir)]
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "set" / "set_set.json").is_file()


def test_convert_name_option_sets_set_name(filters_dir: str, tmp_path) -> None:
    import json

    example = os.path.join(filters_dir, "Markdown", "example.md")
    out_dir = tmp_path / "out"

    result = CliRunner().invoke(
        cli,
        [
            "convert",
            example,
            "Markdown",
            "-o",
            str(out_dir),
            "--name",
            "Problem Sheet 4",
        ],
    )

    assert result.exit_code == 0, result.output
    # The name is slugified for paths but kept verbatim in the set JSON.
    assert (out_dir / "Problem_Sheet_4" / "set_Problem_Sheet_4.json").is_file()
    assert (out_dir / "Problem_Sheet_4.zip").is_file()
    with open(out_dir / "Problem_Sheet_4" / "set_Problem_Sheet_4.json") as file:
        assert json.load(file)["name"] == "Problem Sheet 4"


def test_convert_rejects_unknown_filter(filters_dir: str, tmp_path) -> None:
    example = os.path.join(filters_dir, "PartsSepSol", "example.tex")

    result = CliRunner().invoke(
        cli, ["convert", example, "NotAFilter", "-o", str(tmp_path / "out")]
    )

    assert result.exit_code != 0
    assert "NotAFilter" in result.output
