"""Shared pytest fixtures for the in2lambda test suite."""

import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

import in2lambda
from in2lambda.validation import _node, pdf

needs_compiler = pytest.mark.skipif(
    bool(pdf.missing_tools()),
    reason="compiling the set as the PDF generator does needs pandoc and xelatex",
)
"""The fixtures are reported with the PDF generator's toolchain installed; CI has it."""

EXPORTS_DIR = Path(__file__).parent / "fixtures" / "exports"
"""Real Lambda Feedback exports, one set per folder, exactly as the platform wrote them."""

EXPORTS = sorted(path for path in EXPORTS_DIR.iterdir() if path.is_dir())
"""Every export folder, found rather than listed so that adding one needs no code."""

PROBLEMS_DIR = Path(__file__).parent / "fixtures" / "problems"
"""Hand-written exports, one per folder, each exhibiting one problem for the validator."""

PROBLEM_SETS = sorted(path for path in PROBLEMS_DIR.iterdir() if path.is_dir())
"""Every folder of the above, found the same way: covering a check means adding one."""

SOURCES_DIR = Path(__file__).parent / "fixtures" / "sources"
"""One document per folder for `in2lambda source add`, beside the blocks it should find."""

SOURCES = sorted(path for path in SOURCES_DIR.iterdir() if path.is_dir())
"""Every source folder, so that covering another construct is a folder and no code."""

DRAFTS_DIR = Path(__file__).parent / "fixtures" / "drafts"
"""One document per folder, beside the commands to run against its draft and the result."""

DRAFTS = sorted(path for path in DRAFTS_DIR.iterdir() if path.is_dir())
"""Every draft folder, so that covering another command is a folder and no code."""

SPECS_DIR = Path(__file__).parent / "fixtures" / "specs"
"""One document per folder, beside the spec to run over it and what it should make."""

SPECS = sorted(path for path in SPECS_DIR.iterdir() if path.is_dir())
"""Every spec folder, so that covering another kind of document is a folder and no code."""


AGAINST_CONVERT_DIR = Path(__file__).parent / "fixtures" / "against_convert"
"""One document per folder, beside the spec or commands that take it down both routes."""

AGAINST_CONVERT = sorted(
    path for path in AGAINST_CONVERT_DIR.iterdir() if path.is_dir()
)
"""Every folder of the above, so that covering another document is a folder and no code."""


def key_paths(value: Any, path: str = "") -> set[str]:
    """Every key of a JSON value, at every depth, as ``.parts[0].workedSolution``.

    Args:
        value: A question, a set, or any part of one, as JSON reads it.
        path: What to write in front of each key, for a value taken out of another.

    Returns:
        One path per key, list items numbered, so that two files can be compared by the
        shape they hold rather than by what they say.
    """
    if isinstance(value, dict):
        paths = set()
        for key, item in value.items():
            paths |= {f"{path}.{key}"} | key_paths(item, f"{path}.{key}")
        return paths
    if isinstance(value, list):
        return set().union(
            *(key_paths(item, f"{path}[{i}]") for i, item in enumerate(value))
        )
    return set()


def unexported_keys(written: dict, exported: set[str]) -> list[str]:
    """The keys a written question or set holds that Lambda Feedback never exports there.

    Args:
        written: A question or a set as in2lambda wrote it, as JSON reads it.
        exported: The key paths real exports hold, as :func:`key_paths` reads them off
            one export or off all of them at once.

    Returns:
        The paths of the written file that are in none of them, in order.
    """
    missing = key_paths(written) - exported
    # Lambda Feedback leaves a part's workedSolution out of its export when the part
    # has none, but the writer always emits one, so only then may it be absent.
    for i, part in enumerate(written.get("parts", [])):
        if not part["workedSolution"]["content"]:
            prefix = f".parts[{i}].workedSolution"
            missing = {key for key in missing if not key.startswith(prefix)}
    return sorted(missing)


def frozen_sources(folder: Path) -> list[str]:
    """The documents a draft or spec folder freezes, in the order they are its sources.

    A folder holding a ``solutions.md`` beside its ``source.md`` is a sheet written as
    two documents - the questions, and the worked solutions separately - and freezes as
    two sources, so covering that is a second file in a folder rather than a test.
    """
    return [name for name in ("source.md", "solutions.md") if (folder / name).is_file()]


@pytest.fixture
def without_node(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Runs the test as if Node.js, which KaTeX is rendered with, were not installed.

    Only node is hidden: pandoc must still be found, or a conversion would fail for a
    quite different reason.
    """
    which = shutil.which
    monkeypatch.setattr(
        shutil, "which", lambda command: None if command == "node" else which(command)
    )
    _node.cache_clear()
    yield
    _node.cache_clear()


@pytest.fixture(scope="session")
def filters_dir() -> str:
    """Absolute path to the packaged ``filters`` directory.

    Each filter ships a self-contained ``example.tex`` used by the end-to-end tests.
    """
    return os.path.join(os.path.dirname(in2lambda.__file__), "filters")
