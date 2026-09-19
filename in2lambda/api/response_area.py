"""An answer box in a part, with how Lambda Feedback marks what is typed into it."""

import uuid
from dataclasses import dataclass, field
from typing import Any


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class InputSymbol:
    """A symbol students may type, and what the evaluation function reads it as.

    ``symbol`` is what students see, ``code`` what the evaluator reads, and ``aliases``
    other spellings accepted for it.
    """

    symbol: str
    code: str
    aliases: list[str] = field(default_factory=list)
    is_visible: bool = True


@dataclass
class Test:
    """An author's check of the marking: a response and whether it should be correct."""

    # Its name would otherwise make pytest try to collect it wherever it is imported.
    __test__ = False

    payload: str
    is_correct: bool
    id: str = field(default_factory=_new_id)


@dataclass
class Case:
    """A response that is shown tailored ``feedback``, and may be marked correct."""

    answer: str
    feedback: str
    is_correct: bool
    params: Any = None
    id: str = field(default_factory=_new_id)


@dataclass
class ResponseArea:
    """An answer box as represented on Lambda Feedback.

    Its position among a part's areas is its order, so it holds no order number.
    ``config`` and ``grade_params`` depend on ``response_type`` and are kept as Lambda
    Feedback writes them. The feedback colours and prefixes default to what Lambda
    Feedback fills in.

    Examples:
        >>> from in2lambda.api.response_area import ResponseArea, Test
        >>> area = ResponseArea(
        ...     response_type="NUMERIC_UNITS",
        ...     answer="30 N",
        ...     evaluation_function="comparePhysicalQuantities",
        ...     grade_params={"rtol": 0.05},
        ...     pre_text="$F=$",
        ...     tests=[Test("30 N", True)],
        ... )
        >>> area.tests[0].payload, area.tests[0].is_correct
        ('30 N', True)
    """

    response_type: str = "MATH_SINGLE_LINE"
    """``MATH_SINGLE_LINE``, ``NUMERIC_UNITS`` or ``MULTIPLE_CHOICE``."""
    answer: str | list[bool] = ""
    """The correct answer; for multiple choice, one boolean per option."""
    config: dict[str, Any] | None = None
    evaluation_function: str = "symbolicEqual"
    grade_params: dict[str, Any] | None = None
    pre_text: str = ""
    post_text: str = ""
    content_after: str = ""
    """Markdown shown after the box, before the next one."""
    input_symbols: list[InputSymbol] = field(default_factory=list)
    display_input_symbols: bool = False
    live_preview: bool = False
    include_in_pdf: bool = False
    save_allowed: bool = False
    separate_feedback: bool = True
    common_feedback_color: str = "#C4CDD5"
    correct_feedback_color: str = "#22C55E"
    correct_feedback_prefix: str = "Correct"
    incorrect_feedback_color: str = "#ff5630"
    incorrect_feedback_prefix: str = "Incorrect"
    tests: list[Test] = field(default_factory=list)
    cases: list[Case] = field(default_factory=list)
