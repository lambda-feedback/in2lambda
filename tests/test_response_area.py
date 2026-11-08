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


def test_an_empty_answer_adds_no_test() -> None:
    assert _tests(MultipleChoice(options=["A", "B"])) == []


def _write(tmp_path, area) -> None:
    Set(questions=[Question(parts=[Part(response_areas=[area])])]).to_json(
        str(tmp_path)
    )


@pytest.mark.parametrize(
    "area",
    [
        Number(answer=2.5, tests=[Test("2.5", True)]),
        Number(answer=1, tests=[Test(True, True)]),
        NumericUnits(answer="4 m/s", tests=[Test(4, True)]),
        MultipleChoice(
            options=["A", "B"], answer=[True, False], tests=[Test([True], True)]
        ),
        MultipleChoice(options=["A", "B"], answer=[True]),
        MultipleChoice(
            options=["A", "B"], answer=[True, False], tests=[Test("A", True)]
        ),
    ],
)
def test_a_payload_of_the_wrong_type_or_shape_is_refused(tmp_path, area) -> None:
    with pytest.raises(ValueError, match="Question 1, part a"):
        _write(tmp_path, area)


def test_payloads_of_the_answer_type_are_written(tmp_path) -> None:
    _write(tmp_path, Number(answer=2.5, tests=[Test(3, False)]))
    _write(
        tmp_path,
        MultipleChoice(
            options=["A", "B"], answer=[True, False], tests=[Test([False, True], False)]
        ),
    )


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


def test_accept_and_reject_are_written_as_tests_after_the_answer() -> None:
    area = NumericUnits(answer="4 m/s", accept=["400 cm/s", "4 m/s"], reject=["4 km/h"])
    assert _tests(area) == [("4 m/s", True), ("400 cm/s", True), ("4 km/h", False)]


def test_a_response_both_accepted_and_rejected_is_refused(tmp_path) -> None:
    with pytest.raises(ValueError, match="both accepted and rejected"):
        _write(tmp_path, NumericUnits(answer="4 m/s", reject=["4 m/s"]))


def test_each_wrong_option_alone_is_a_failing_test() -> None:
    area = MultipleChoice(options=["A", "B", "C"], answer=[False, True, False])
    assert _tests(area) == [
        ([False, True, False], True),
        ([True, False, False], False),
        ([False, False, True], False),
    ]


def test_a_multi_select_also_fails_one_correct_option_and_all_options() -> None:
    area = MultipleChoice(options=["A", "B", "C"], answer=[True, True, False])
    assert _tests(area)[1:] == [
        ([False, False, True], False),
        ([True, False, False], False),
        ([True, True, True], False),
    ]
