"""Converting a document without pandoc or panflute says what to install."""

import os
import shutil
import sys

import pytest
from click.testing import CliRunner

from in2lambda.main import ConversionToolsMissing, cli, runner

PANDOC_HINT = "pandoc.org/installing"
PANFLUTE_HINT = "pip install 'in2lambda[convert]'"


@pytest.mark.parametrize(
    "pandoc_missing, panflute_missing",
    [(True, True), (True, False), (False, True)],
)
def test_runner_names_what_is_missing(
    pandoc_missing: bool, panflute_missing: bool, monkeypatch, tmp_path
) -> None:
    """The error names each missing tool, and only those."""
    if pandoc_missing:
        monkeypatch.setattr(shutil, "which", lambda _: None)
    if panflute_missing:
        monkeypatch.setitem(sys.modules, "panflute", None)

    # The file does not exist, so reading it first would raise FileNotFoundError.
    with pytest.raises(ConversionToolsMissing) as error:
        runner(str(tmp_path / "missing.tex"), "PartsSepSol")

    assert (PANDOC_HINT in str(error.value)) == pandoc_missing
    assert (PANFLUTE_HINT in str(error.value)) == panflute_missing


def test_cli_exits_with_message(filters_dir: str, monkeypatch, tmp_path) -> None:
    """The command line prints the install instructions, not a traceback."""
    monkeypatch.setitem(sys.modules, "panflute", None)
    example = os.path.join(filters_dir, "PartsSepSol", "example.tex")

    result = CliRunner().invoke(cli, [example, "PartsSepSol", "-o", str(tmp_path)])

    assert result.exit_code != 0
    assert PANFLUTE_HINT in result.output
    assert isinstance(result.exception, SystemExit)
