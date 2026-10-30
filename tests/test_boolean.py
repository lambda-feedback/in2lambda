"""A Boolean area is written as Lambda Feedback's own teacher test sends it."""

from in2lambda.api.response_area import Boolean
from in2lambda.json_convert.json_convert import _response_area_to_json


def test_a_boolean_answer_is_written_as_a_number_compared_as_a_string() -> None:
    area = _response_area_to_json(Boolean(answer=True), 0)
    assert area["response"]["responseInput"]["answer"] == 1
    assert area["gradeParams"] == {"type": "str"}
