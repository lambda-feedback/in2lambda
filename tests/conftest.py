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


@pytest.fixture(scope="session")
def filters_dir() -> str:
    """Absolute path to the packaged ``filters`` directory.

    Each filter ships a self-contained ``example.tex`` used by the end-to-end tests.
    """
    return os.path.join(os.path.dirname(in2lambda.__file__), "filters")
