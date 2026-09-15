"""Round-trips every real Lambda Feedback export through the in2lambda model.

Each folder in ``fixtures/exports`` is loaded into a :class:`~in2lambda.api.set.Set`,
written back with :meth:`~in2lambda.api.set.Set.to_json` and compared with the
original. The model holds far less than an export, so the comparison covers what it
does hold, the file names written, and that the writer emits no key Lambda Feedback
does not.
"""

import json
from pathlib import Path

import pytest
from conftest import EXPORTS, load_export

from in2lambda.api.set import Set

pytestmark = pytest.mark.parametrize("export_dir", EXPORTS, ids=lambda path: path.name)


def _write_back(question_set: Set, tmp_path: Path) -> Path:
    question_set.to_json(str(tmp_path / "out"))
    return tmp_path / "out" / question_set._name


def _relative_files(directory: Path) -> list[str]:
    # Finder leaves .DS_Store beside files it has shown; it is not part of an export.
    return sorted(
        str(path.relative_to(directory))
        for path in directory.rglob("*")
        if path.is_file() and not path.name.startswith(".")
    )


def _modelled(question_set: Set) -> dict:
    # Visibility controllers have no equality, and image paths differ by where the
    # set was read from, so compare their values and file names.
    return {
        "name": question_set._name,
        "description": question_set._description,
        "visibility": [
            str(question_set._finalAnswerVisibility),
            str(question_set._workedSolutionVisibility),
            str(question_set._structuredTutorialVisibility),
        ],
        "questions": [
            (q.title, q.main_text, q.parts, [Path(image).name for image in q.images])
            for q in question_set.questions
        ],
    }


def _key_paths(value, path: str = "") -> set[str]:
    if isinstance(value, dict):
        paths = set()
        for key, item in value.items():
            paths |= {f"{path}.{key}"} | _key_paths(item, f"{path}.{key}")
        return paths
    if isinstance(value, list):
        return set().union(
            *(_key_paths(item, f"{path}[{i}]") for i, item in enumerate(value))
        )
    return set()


def _unexported_keys(written: dict, exported: dict) -> list[str]:
    missing = _key_paths(written) - _key_paths(exported)
    # Lambda Feedback leaves a part's workedSolution out of its export when the part
    # has none, but the writer always emits one, so only then may it be absent.
    for i, part in enumerate(written.get("parts", [])):
        if not part["workedSolution"]["content"]:
            prefix = f".parts[{i}].workedSolution"
            missing = {key for key in missing if not key.startswith(prefix)}
    return sorted(missing)


def test_export_round_trips(export_dir: Path, tmp_path: Path) -> None:
    """Writing a loaded export reproduces its file names and reloads to the same set."""
    loaded = load_export(export_dir)
    assert loaded.questions
    assert all(question.main_text or question.parts for question in loaded.questions)

    written = _write_back(loaded, tmp_path)

    assert _relative_files(written) == _relative_files(export_dir)
    assert _modelled(load_export(written)) == _modelled(loaded)


def test_written_keys_exist_in_export(export_dir: Path, tmp_path: Path) -> None:
    """The writer emits no key, at any depth, that Lambda Feedback never exports there."""
    written = _write_back(load_export(export_dir), tmp_path)

    missing = {}
    for file in written.glob("*.json"):
        exported = json.loads((export_dir / file.name).read_text())
        keys = _unexported_keys(json.loads(file.read_text()), exported)
        if keys:
            missing[file.name] = keys
    assert not missing, missing
