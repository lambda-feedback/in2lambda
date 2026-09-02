"""Response areas: the data model, the registry, and the JSON they produce."""

import json
from pathlib import Path

import pytest

from in2lambda.api.question import Question
from in2lambda.api.response_area import ResponseArea
from in2lambda.api.set import Set
from in2lambda.json_convert import json_convert
from in2lambda.response_areas import registry

FIXTURES = Path(__file__).parent / "fixtures" / "response_areas"


def _load_ra_template() -> dict:
    path = Path(json_convert.__file__).with_name(
        json_convert.MINIMAL_RESPONSE_AREA_TEMPLATE
    )
    return json.loads(path.read_text())


def test_add_response_area_creates_a_part_when_needed() -> None:
    question = Question()
    question.add_response_area(ResponseArea("BOOLEAN", "True", "compareBoolean"))
    assert len(question.parts) == 1
    assert question.parts[0].response_areas[0].evaluation_function == "compareBoolean"


def test_response_areas_are_hidden_from_repr() -> None:
    # The many doctests that assert on Part(...) / Question(...) output rely on this.
    question = Question()
    question.add_part_text("a")
    question.add_response_area(ResponseArea("NUMBER", "4", "isExactEqual"))
    assert "response_areas" not in repr(question)


def test_json_matches_the_exported_code_shape() -> None:
    fixture = json.loads((FIXTURES / "code_evaluatepython.json").read_text())
    response_area = ResponseArea(
        response_type="CODE",
        answer=fixture["response"]["responseInput"]["answer"],
        evaluation_function="evaluatePython",
        grade_params={"mode": "unit_test", "use_answer_as_test_code": True},
        config={"language": "python"},
    )

    built = json_convert._response_area_json(response_area, _load_ra_template(), 0)

    assert built == fixture


def test_convert_emits_populated_response_area(tmp_path) -> None:
    set_obj = Set()
    set_obj.add_question(main_text="A question")
    set_obj.current_question.add_part_text("Give an expression for the area.")
    set_obj.current_question.add_response_area(
        ResponseArea("EXPRESSION", "pi*r**2", "compareExpressions", {"rtol": 0.01})
    )
    set_obj.to_json(str(tmp_path / "out"))

    question = json.loads(
        next((tmp_path / "out" / "set").glob("question_*.json")).read_text()
    )
    area = question["parts"][0]["responseAreas"][0]
    assert area["evaluationFunctionName"] == "compareExpressions"
    assert area["gradeParams"] == {"rtol": 0.01}
    assert area["response"]["responseInput"] == {
        "responseType": "EXPRESSION",
        "answer": "pi*r**2",
        "config": {},
    }
    # The reference answer is mirrored into the part's final-answer field.
    assert question["parts"][0]["answerContent"] == "pi*r**2"


def test_parts_without_response_areas_stay_empty(tmp_path) -> None:
    set_obj = Set()
    set_obj.add_question(main_text="Plain question")
    set_obj.current_question.add_part_text("No auto-marking here.")
    set_obj.to_json(str(tmp_path / "out"))

    question = json.loads(
        next((tmp_path / "out" / "set").glob("question_*.json")).read_text()
    )
    assert question["parts"][0]["responseAreas"] == []
    assert question["parts"][0]["answerContent"] == ""


@pytest.mark.parametrize(
    "name", ["compareExpressions", "comparePhysicalQuantities", "compareBoolean"]
)
def test_registry_has_the_documented_functions(name: str) -> None:
    spec = registry.get(name)
    assert spec is not None
    assert spec.response_types  # every function pairs with at least one input type


def test_registry_functions_for_response_type() -> None:
    assert registry.functions_for("BOOLEAN") == ["compareBoolean"]
    assert "compareExpressions" in registry.functions_for("EXPRESSION")
