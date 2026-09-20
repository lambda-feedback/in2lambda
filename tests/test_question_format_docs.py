"""The question format page's key tables are generated from the real exports.

``docs/source/question_format.py`` builds them at docs build. Running the same
generator here means a key Lambda Feedback adds to an export fails the test suite
until someone writes down what it means, rather than a docs build nobody watches.
"""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from conftest import EXPORTS

_module_path = Path(__file__).parents[1] / "docs" / "source" / "question_format.py"
_spec = importlib.util.spec_from_file_location("question_format", _module_path)
question_format = importlib.util.module_from_spec(_spec)
# Loaded by path because docs/source is not a package and holds Sphinx's conf.py.
_spec.loader.exec_module(question_format)


def _table_keys(table: Path) -> list[str]:
    """The key column of a generated table, without its header rows."""
    return [
        line.split("|")[1].strip(" `") for line in table.read_text().splitlines()[2:]
    ]


def _exported_keys(pattern: str) -> set[str]:
    return {
        key
        for export_dir in EXPORTS
        for file in export_dir.glob(pattern)
        for key in json.loads(file.read_text())
    }


def test_tables_cover_the_exported_keys(tmp_path: Path) -> None:
    """Each table lists the keys its exports carry, every one of them with a note."""
    question_format.generate_question_format_tables(EXPORTS, tmp_path)

    assert set(_table_keys(tmp_path / "set.md")) == _exported_keys("set_*.json")
    assert set(_table_keys(tmp_path / "question.md")) == _exported_keys(
        "question_*.json"
    )
    # Objects a key holds are flattened onto their parent's table.
    assert "workedSolution.content" in _table_keys(tmp_path / "part.md")
    assert "response.responseInput.config" in _table_keys(tmp_path / "response_area.md")


# An empty object holds no keys to descend into, so it has to be a row in its own
# right for a new key to be named rather than silently dropped.
@pytest.mark.parametrize("value", [1, {}])
def test_a_key_with_no_note_is_named(value: object, tmp_path: Path) -> None:
    """A key added to the schema stops the build, saying which key needs a note."""
    export_dir = Path(shutil.copytree(EXPORTS[0], tmp_path / "export"))
    file = sorted(export_dir.glob("question_*.json"))[0]
    question = json.loads(file.read_text())
    question["madeUp"] = value
    file.write_text(json.dumps(question))

    with pytest.raises(ValueError, match="madeUp"):
        question_format.generate_question_format_tables([export_dir], tmp_path / "out")
