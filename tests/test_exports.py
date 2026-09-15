"""Round-trips every real Lambda Feedback export through the in2lambda model.

Each folder in ``fixtures/exports`` is loaded with
:meth:`~in2lambda.api.set.Set.from_json`, written back with
:meth:`~in2lambda.api.set.Set.to_json` and compared with the original. The model holds
far less than an export, so the comparison covers what it does hold, the file names
written, and that the writer emits no key Lambda Feedback does not.
"""

import json
import re
from pathlib import Path

import pytest
from conftest import EXPORTS

from in2lambda.api.set import Set

each_export = pytest.mark.parametrize("export_dir", EXPORTS, ids=lambda path: path.name)


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


@each_export
def test_export_round_trips(export_dir: Path, tmp_path: Path) -> None:
    """Writing a loaded export reproduces its file names and reloads to the same set."""
    loaded = Set.from_json(str(export_dir))
    assert loaded.questions
    assert all(question.main_text or question.parts for question in loaded.questions)

    written = _write_back(loaded, tmp_path)

    assert _relative_files(written) == _relative_files(export_dir)
    assert _modelled(Set.from_json(str(written))) == _modelled(loaded)
    assert _modelled(Set.from_json(f"{written}.zip")) == _modelled(loaded)

    # Text added to a loaded question is a new part, not a rewrite of the first.
    question = Set.from_json(str(export_dir)).questions[0]
    texts_before = [part.text for part in question.parts]
    question.add_part_text("added")
    assert [part.text for part in question.parts] == texts_before + ["added"]


@each_export
def test_written_keys_exist_in_export(export_dir: Path, tmp_path: Path) -> None:
    """The writer emits no key, at any depth, that Lambda Feedback never exports there."""
    written = _write_back(Set.from_json(str(export_dir)), tmp_path)

    missing = {}
    for file in written.glob("*.json"):
        exported = json.loads((export_dir / file.name).read_text())
        keys = _unexported_keys(json.loads(file.read_text()), exported)
        if keys:
            missing[file.name] = keys
    assert not missing, missing


def test_from_json_rejects_folder_without_set(tmp_path: Path) -> None:
    """A folder with no set file is refused with an error that says where it looked."""
    (tmp_path / "question_000_Q.json").write_text("{}")
    with pytest.raises(ValueError, match=re.escape(str(tmp_path))):
        Set.from_json(str(tmp_path))
