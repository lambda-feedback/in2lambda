"""Round-trips every real Lambda Feedback export through the in2lambda model.

Each folder in ``fixtures/exports`` is loaded with
:meth:`~in2lambda.api.set.Set.from_json`, written back with
:meth:`~in2lambda.api.set.Set.to_json` and compared with the original. The model holds
far less than an export, so the comparison covers what it does hold, the file names
written, and that the writer emits no key Lambda Feedback does not.
"""

import json
import re
import uuid
from pathlib import Path

import pytest
from conftest import EXPORTS

from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.response_area import Case, InputSymbol, ResponseArea, Test
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
    # An export may list a part's areas out of order; the writer puts them in order,
    # so compare each written area with the exported one of the same number.
    for part in exported.get("parts", []):
        part["responseAreas"].sort(key=lambda area: area["orderNumber"])
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

    # Reloading alone would pass if answers and areas were dropped or mismapped the
    # same way both ways, so compare what is written with the export itself.
    for file in written.glob("question_*.json"):
        written_parts = json.loads(file.read_text())["parts"]
        exported_parts = json.loads((export_dir / file.name).read_text())["parts"]
        assert [
            (part["answerContent"], part["responseAreas"]) for part in written_parts
        ] == [
            (
                part["answerContent"],
                sorted(part["responseAreas"], key=lambda area: area["orderNumber"]),
            )
            for part in exported_parts
        ], file.name

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


def _area_shape(area: dict) -> frozenset[str]:
    # Without indices, an area's shape is the keys it has, not how many tests, cases
    # or symbols it lists.
    return frozenset(re.sub(r"\[\d+\]", "[]", path) for path in _key_paths(area))


def test_response_areas_built_in_python_write_as_exported(tmp_path: Path) -> None:
    """Boxes of each exported type built in Python reload unchanged, shaped as exported."""
    part = Part(
        text="Find the drag, then say whether it scales.",
        response_areas=[
            ResponseArea(
                response_type="MATH_SINGLE_LINE",
                answer="(pi/6)*rho*U**2*R**2",
                config={
                    "allowPhoto": True,
                    "allowHandwrite": True,
                    "enableRefinement": True,
                },
                evaluation_function="symbolicEqual",
                grade_params={"strict_syntax": False},
                pre_text="$D=$",
                content_after="Now put in the numbers.",
                input_symbols=[InputSymbol("\\(R\\)", "R", ["r"])],
                tests=[Test("(pi/6)*rho*U**2*R**2", True)],
                cases=[Case("pi*rho*U**2*R**2", "A factor is missing.", False)],
            ),
            ResponseArea(
                response_type="NUMERIC_UNITS",
                answer="30 N",
                evaluation_function="comparePhysicalQuantities",
                grade_params={"rtol": 0.05, "strict_syntax": False},
                tests=[Test("30 N", True), Test("30", False)],
                cases=[
                    Case("30 kg m s-2", "Put negative exponents in brackets.", False)
                ],
            ),
            ResponseArea(
                response_type="MULTIPLE_CHOICE",
                answer=[True, False],
                config={"single": True, "options": ["Yes", "No"], "randomise": False},
                evaluation_function="arrayEqual",
            ),
        ],
    )
    written = _write_back(Set(questions=[Question(parts=[part])]), tmp_path)

    # Equality includes the ids, so reloading must keep the ones that were written.
    assert Set.from_json(str(written)).questions[0].parts == [part]

    (question_file,) = written.glob("question_*.json")
    written_areas = json.loads(question_file.read_text())["parts"][0]["responseAreas"]

    # Import needs every test and case given no id to be written with its own uuid.
    ids = [
        item["id"] for area in written_areas for item in area["tests"] + area["cases"]
    ]
    assert len(set(ids)) == 5
    assert all(uuid.UUID(id_) for id_ in ids)

    exported_shapes = {
        _area_shape(area)
        for export_dir in EXPORTS
        for file in export_dir.glob("question_*.json")
        for exported_part in json.loads(file.read_text())["parts"]
        for area in exported_part["responseAreas"]
    }
    for area in written_areas:
        assert _area_shape(area) in exported_shapes, area["response"]


def test_from_json_rejects_folder_without_set(tmp_path: Path) -> None:
    """A folder with no set file is refused with an error that says where it looked."""
    (tmp_path / "question_000_Q.json").write_text("{}")
    with pytest.raises(ValueError, match=re.escape(str(tmp_path))):
        Set.from_json(str(tmp_path))
