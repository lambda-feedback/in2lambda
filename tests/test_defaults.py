"""in2lambda's defaults fill in the settings an author leaves unset."""

import pytest

from in2lambda.api.response_area import MathMultiLines


def test_a_type_without_a_default_evaluation_function_needs_one() -> None:
    with pytest.raises(TypeError):
        MathMultiLines()
