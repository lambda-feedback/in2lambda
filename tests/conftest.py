"""Shared pytest fixtures for the in2lambda test suite."""

import os
from pathlib import Path

import pytest

import in2lambda

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


@pytest.fixture(scope="session")
def filters_dir() -> str:
    """Absolute path to the packaged ``filters`` directory.

    Each filter ships a self-contained ``example.tex`` used by the end-to-end tests.
    """
    return os.path.join(os.path.dirname(in2lambda.__file__), "filters")
