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
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import EXPORTS, key_paths, unexported_keys

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
    # set was read from, so compare their values and file names. Questions are
    # compared whole, so a field added to Question is compared without editing this.
    return {
        "name": question_set._name,
        "description": question_set._description,
        "visibility": [
            str(question_set._finalAnswerVisibility),
            str(question_set._workedSolutionVisibility),
            str(question_set._structuredTutorialVisibility),
        ],
        "questions": [
            replace(q, images=[Path(image).name for image in q.images])
            for q in question_set.questions
        ],
    }


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
        # An export may list a part's areas out of order; the writer puts them in
        # order, so compare each written area with the exported one of the same number.
        for part in exported.get("parts", []):
            part["responseAreas"].sort(key=lambda area: area["orderNumber"])
        keys = unexported_keys(json.loads(file.read_text()), key_paths(exported))
        if keys:
            missing[file.name] = keys
    assert not missing, missing


@each_export
def test_question_exports_alone(export_dir: Path, tmp_path: Path) -> None:
    """Each question writes on its own as the set writes it, with the images it uses."""
    loaded = Set.from_json(str(export_dir))
    from_set = _write_back(loaded, tmp_path)
    exported_media = _relative_files(export_dir / "media")

    for i, question in enumerate(loaded.questions):
        question.to_json(str(tmp_path / "single"), number=i)

        # The question writes under the name the set gives it, so the files the set
        # wrote for the same number say what to expect.
        (set_file,) = from_set.glob(f"question_{i:03}_*.json")
        folder = tmp_path / "single" / set_file.stem
        expected = sorted(
            [set_file.name]
            + [
                f"media/{name}"
                for name in exported_media
                if name.startswith(f"{set_file.stem}_")
            ]
        )

        assert _relative_files(folder) == expected
        with zipfile.ZipFile(f"{folder}.zip") as zf:
            assert sorted(zf.namelist()) == expected

        written = (folder / set_file.name).read_text()
        assert json.loads(written) == json.loads(set_file.read_text())

        # Every image the JSON points at must be beside it, or it will not resolve
        # once the question is imported.
        references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", written)
        assert all(
            (folder / "media" / reference).is_file() for reference in references
        ), references


def test_writing_leaves_other_files(tmp_path: Path) -> None:
    """Writing over an export keeps files it did not write and leaves them out of the zip."""
    image = tmp_path / "diagram.png"
    image.write_bytes(b"not really a png")
    question_set = Set(questions=[Question(title="Q", images=[str(image)])])

    written = _write_back(question_set, tmp_path)
    strays = [
        tmp_path / "out" / "notes.txt",
        written / "notes.txt",
        written / "media" / "notes.txt",
    ]
    for stray in strays:
        stray.write_text("someone else's work")

    _write_back(question_set, tmp_path)

    assert [stray.read_text() for stray in strays] == ["someone else's work"] * 3
    with zipfile.ZipFile(f"{written}.zip") as zf:
        assert sorted(zf.namelist()) == [
            "media/diagram.png",
            "question_000_Q.json",
            "set_set.json",
        ]


def test_repeated_image_zipped_once(tmp_path: Path) -> None:
    """An image listed twice, as one used in both a question and its solution, is one file."""
    image = tmp_path / "diagram.png"
    image.write_bytes(b"not really a png")
    question_set = Set(questions=[Question(title="Q", images=[str(image), str(image)])])

    written = _write_back(question_set, tmp_path)

    assert _relative_files(written / "media") == ["diagram.png"]
    with zipfile.ZipFile(f"{written}.zip") as zf:
        assert [name for name in zf.namelist() if name.startswith("media/")] == [
            "media/diagram.png"
        ]


def test_two_figures_of_one_name_are_both_carried(tmp_path: Path) -> None:
    """media/ is flat, so the second of two files called the same is named as an export names one."""
    for folder, content in (("a", b"first diagram"), ("b", b"second diagram")):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "diagram.png").write_bytes(content)
    question_set = Set(
        questions=[
            Question(
                title=title,
                main_text=f"As shown in ![diagram.png]({folder}/diagram.png).",
                images=[str(tmp_path / folder / "diagram.png")],
            )
            for title, folder in (("First", "a"), ("Second", "b"))
        ]
    )

    written = _write_back(question_set, tmp_path)

    assert _relative_files(written / "media") == [
        "diagram.png",
        "question_001_Second_0001.png",
    ]
    assert (written / "media" / "diagram.png").read_bytes() == b"first diagram"
    assert [
        json.loads((written / file).read_text())["masterContent"]
        for file in ("question_000_First.json", "question_001_Second.json")
    ] == [
        "As shown in ![diagram.png](diagram.png).",
        "As shown in ![diagram.png](question_001_Second_0001.png).",
    ]


def test_one_question_telling_two_figures_of_a_name_apart(tmp_path: Path) -> None:
    """The only case where which image a reference names is a question, answered by the path."""
    for folder, content in (("a", b"first diagram"), ("b", b"second diagram")):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "diagram.png").write_bytes(content)
    question_set = Set(
        questions=[
            Question(
                title="Q",
                # A document writes a reference as it sits beside the document, so a
                # sheet in a folder of its own climbs out of it to reach the figures,
                # and the resolved path listed below has no trace of the climb.
                main_text="Before, ![](../a/diagram.png).",
                parts=[Part(text="After, ![](../b/diagram.png).")],
                images=[
                    str(tmp_path / "a" / "diagram.png"),
                    str(tmp_path / "b" / "diagram.png"),
                ],
            )
        ]
    )

    written = _write_back(question_set, tmp_path)

    assert _relative_files(written / "media") == [
        "diagram.png",
        "question_000_Q_0001.png",
    ]
    assert (written / "media" / "diagram.png").read_bytes() == b"first diagram"
    question = json.loads((written / "question_000_Q.json").read_text())
    assert question["masterContent"] == "Before, ![](diagram.png)."
    assert question["parts"][0]["content"] == "After, ![](question_000_Q_0001.png)."


def test_one_figure_used_by_two_questions_is_copied_once(tmp_path: Path) -> None:
    """Both questions refer to the one file, under the one name it is carried as."""
    image = tmp_path / "figures" / "diagram.png"
    image.parent.mkdir()
    image.write_bytes(b"not really a png")
    question_set = Set(
        questions=[
            Question(
                title=title,
                main_text="As shown in ![diagram.png](figures/diagram.png).",
                images=[str(image)],
            )
            for title in ("First", "Second")
        ]
    )

    written = _write_back(question_set, tmp_path)

    assert _relative_files(written / "media") == ["diagram.png"]
    assert [
        json.loads(file.read_text())["masterContent"]
        for file in sorted(written.glob("question_*.json"))
    ] == ["As shown in ![diagram.png](diagram.png)."] * 2


def _area_shape(area: dict) -> frozenset[str]:
    # Without indices, an area's shape is the keys it has, not how many tests, cases
    # or symbols it lists.
    return frozenset(re.sub(r"\[\d+\]", "[]", path) for path in key_paths(area))


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


def test_question_settings_are_written(tmp_path: Path) -> None:
    """A question's settings reach its JSON, are left out when unset, and reload."""
    question_set = Set(_name="Settings")
    question_set.questions = [
        Question(
            title="Configured",
            # A whole number, as an export holds the highest skill level; the
            # fixture's questions cover fractional ones.
            skill=1,
            guidance="Try part a first.",
            duration_lower_bound=5,
            duration_upper_bound=10,
            publish=False,
            display_final_answer=False,
            display_worked_solution=False,
            display_structured_tutorial=False,
            display_chatbot=False,
        ),
        Question(title="Default"),
    ]
    written = _write_back(question_set, tmp_path)

    configured = json.loads((written / "question_000_Configured.json").read_text())
    assert {
        key: configured[key]
        for key in [
            "skill",
            "guidance",
            "durationLowerBound",
            "durationUpperBound",
            "publish",
            "displayFinalAnswer",
            "displayWorkedSolution",
            "displayStructuredTutorial",
            "displayChatbot",
        ]
    } == {
        "skill": 1,
        "guidance": "Try part a first.",
        "durationLowerBound": 5,
        "durationUpperBound": 10,
        "publish": False,
        "displayFinalAnswer": False,
        "displayWorkedSolution": False,
        "displayStructuredTutorial": False,
        "displayChatbot": False,
    }

    default = json.loads((written / "question_001_Default.json").read_text())
    assert default["publish"] is True
    assert default["displayChatbot"] is True
    assert not {"skill", "guidance", "durationLowerBound", "durationUpperBound"} & set(
        default
    )

    # Only the settings are compared: a question written without parts reloads with
    # the template's placeholder part.
    def settings(question: Question) -> list:
        return [
            question.skill,
            question.guidance,
            question.duration_lower_bound,
            question.duration_upper_bound,
            question.publish,
            question.display_final_answer,
            question.display_worked_solution,
            question.display_structured_tutorial,
            question.display_chatbot,
        ]

    reloaded = Set.from_json(str(written)).questions
    assert [settings(q) for q in reloaded] == [
        settings(q) for q in question_set.questions
    ]


def test_from_json_rejects_folder_without_set(tmp_path: Path) -> None:
    """A folder with no set file is refused with an error that says where it looked."""
    (tmp_path / "question_000_Q.json").write_text("{}")
    with pytest.raises(ValueError, match=re.escape(str(tmp_path))):
        Set.from_json(str(tmp_path))
