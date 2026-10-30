"""Response areas as in2lambda writes them."""

import pytest

from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.response_area import (
    InputSymbol,
    MultipleChoice,
    Number,
    NumericUnits,
    Test,
)
from in2lambda.api.set import Set
from in2lambda.json_convert.json_convert import _response_area_to_json


def _tests(area) -> list:
    return [
        (t["payload"], t["expectedResponse"]["isCorrect"])
        for t in _response_area_to_json(area, 0)["tests"]
    ]


def test_a_test_payload_keeps_its_python_type() -> None:
    assert _tests(Number(tests=[Test(2.5, True)])) == [(2.5, True)]


def test_the_answer_is_written_as_a_passing_test_once() -> None:
    assert _tests(NumericUnits(answer="4 m/s")) == [("4 m/s", True)]
    assert _tests(NumericUnits(answer="4 m/s", tests=[Test("4 m/s", True)])) == [
        ("4 m/s", True)
    ]


def test_an_empty_list_answer_is_written_as_a_failing_test() -> None:
    assert _tests(MultipleChoice(options=["A", "B"])) == [([], False)]


def test_greek_aliases_cover_subscripts_and_unicode_forms() -> None:
    assert InputSymbol.greek("$\\sigma_f$", "sigma_f").aliases == [
        "sigma_{f}",
        "σ_f",
        "σ_{f}",
        "𝜎_f",
        "𝜎_{f}",
        "ς_f",
        "ς_{f}",
    ]
    with pytest.raises(ValueError):
        InputSymbol.greek("$x$", "x")


def test_a_set_with_no_correct_multiple_choice_option_is_not_written(
    tmp_path,
) -> None:
    area = MultipleChoice(options=["A", "B"], answer=[False, False])
    s = Set(questions=[Question(parts=[Part(response_areas=[area])])])
    earlier = tmp_path / "earlier.json"
    earlier.write_text("{}")
    with pytest.raises(ValueError, match="Question 1, part a"):
        s.to_json(str(tmp_path))
    assert earlier.exists()
