"""A set written by in2lambda must hold the keys a real Lambda Feedback export holds.

The platform's export is the only definition of the format. A set using every field
in2lambda has is written out, and the keys of its files are compared with those of the
exports under ``fixtures/exports``. The keys of ``config`` are compared per response
type; those of ``gradeParams`` and a case's ``params`` belong to the evaluation function.
"""

import json
from pathlib import Path

from in2lambda.api import response_area
from in2lambda.api.part import Part
from in2lambda.api.question import Question
from in2lambda.api.response_area import Case, Color, InputSymbol, MathSingleLine, Test
from in2lambda.api.set import Set

EXPORTS = sorted((Path(__file__).parent / "fixtures" / "exports").glob("*/"))

# Lambda Feedback sometimes writes an empty title on a tutorial or worked solution;
# only its branches have titles, so in2lambda writes none.
NOT_WRITTEN = {".parts[].tutorial.title", ".parts[].workedSolution.title"}


def _keys(value, path=""):
    """Every key path of a JSON value, with list items merged under ``[]``."""
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(f"{path}.{key}")
            if key not in ("config", "gradeParams", "params"):
                found |= _keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for item in value:
            found |= _keys(item, f"{path}[]")
    return found


def _exported(pattern: str) -> list:
    return [json.loads(f.read_text()) for e in EXPORTS for f in e.glob(pattern)]


def test_a_set_using_every_field_writes_the_keys_of_a_real_export(tmp_path) -> None:
    area = MathSingleLine(
        answer="2*x",
        evaluation_function="compareExpressions",
        input_symbols=[InputSymbol("$x$", "x", ["X"])],
        tests=[Test("2*x", True)],
        cases=[Case("x", "Twice that.", False, color=Color.AMBER)],
    )
    question = Question(
        title="Q",
        parts=[
            Part(
                content="Find it.",
                response_areas=[area],
                tutorial="Double it.",
                answer="$2x$",
                worked_solution="Since...",
            ),
            Part(content="No solution here."),
        ],
        skill=0.5,
        guidance="A warm-up.",
        duration_lower_bound=5,
        duration_upper_bound=10,
    )
    s = Set(released_at="2026-09-28T11:00:00.000Z", questions=[question])
    s.to_json(str(tmp_path))

    written = tmp_path / "set"
    exported_set = set().union(*map(_keys, _exported("set_*.json")))
    assert _keys(json.loads((written / "set_set.json").read_text())) == exported_set
    (question_file,) = written.glob("question_*.json")
    exported_question = set().union(*map(_keys, _exported("question_*.json")))
    assert (
        _keys(json.loads(question_file.read_text())) == exported_question - NOT_WRITTEN
    )


def test_each_response_type_writes_the_settings_of_a_real_export() -> None:
    def subclasses(cls):
        return [s for c in cls.__subclasses__() for s in [c, *subclasses(c)]]

    types = {
        cls.response_type: cls
        for cls in subclasses(response_area.ResponseArea)
        if "response_type" in vars(cls)
    }
    for question in _exported("question_*.json"):
        for part in question["parts"]:
            for area in part["responseAreas"]:
                response = area["response"]["responseInput"]
                written = types[response["responseType"]](evaluation_function="")
                assert set(written._config() or {}) == set(response["config"] or {})
