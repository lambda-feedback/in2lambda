"""A user's TOML file overrides in2lambda's defaults, and a mistake in it is refused."""

import copy

import pytest

from in2lambda import defaults
from in2lambda.api.question import Question
from in2lambda.api.response_area import MathMultiLines, MathSingleLine


@pytest.fixture(autouse=True)
def packaged_defaults(monkeypatch) -> None:
    monkeypatch.setattr(defaults, "_DEFAULTS", copy.deepcopy(defaults._DEFAULTS))


def test_a_users_file_overrides_only_what_it_sets(tmp_path) -> None:
    ours = tmp_path / "ours.toml"
    ours.write_text(
        "[question]\npublish = false\n"
        '[response_area.MATH_MULTI_LINES]\nevaluation_function = "evaluateProof"\n'
    )
    defaults.override(str(ours))

    assert Question().publish is False
    assert Question().display_chatbot is True
    assert MathMultiLines().evaluation_function == "evaluateProof"
    assert MathSingleLine().evaluation_function == "compareExpressions"


@pytest.mark.parametrize(
    "text",
    [
        "[question]\npublsh = false\n",
        "[response_area.GRAPH]\nlive_preview = true\n",
        '[question]\npublish = "no"\n',
        '[set]\nchatbot_visibility = "SHOWN"\n',
        "[question]\npublish = true\npublish = false\n",
    ],
    ids=["unknown key", "unknown type", "wrong type", "unknown visibility", "repeat"],
)
def test_a_users_file_with_a_mistake_is_refused(tmp_path, text: str) -> None:
    ours = tmp_path / "ours.toml"
    ours.write_text(text)
    with pytest.raises(ValueError):
        defaults.override(str(ours))


def test_a_refused_file_changes_nothing(tmp_path) -> None:
    ours = tmp_path / "ours.toml"
    ours.write_text("[question]\npublish = false\npublsh = false\n")
    with pytest.raises(ValueError):
        defaults.override(str(ours))
    assert Question().publish is True


def test_a_type_without_a_default_evaluation_function_needs_one() -> None:
    with pytest.raises(TypeError):
        MathMultiLines()
