"""An area for student responses that will receive automated feedback."""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Optional, Union


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class InputSymbol:
    """Defines symbols and how to enter them into a response area.

    Fields per symbol:
    - ``symbol`` for display to users (markdown, typically dollar-delimited math latex)
    - ``code`` for users to input (plan text, fed to the algorithm and also be rendered to users within backticks as `code`)
    - ``aliases`` list of alternative code inputs, to be substituted by the `code` field when evaluating
    - ``is_visible`` Boolean, whether to display input symbol info to users (in addition to always sending it to the evaluator to help parsing)
    """

    symbol: str
    code: str
    aliases: list[str] = field(default_factory=list)
    is_visible: bool = True


@dataclass
class Test:
    """Teacher author's assertions of how responses should be evaluated."""

    # Its name would otherwise make pytest try to collect it wherever it is imported.
    __test__ = False

    payload: str
    is_correct: bool
    id: str = field(default_factory=_new_id)


class Color(Enum):
    """Acceptable colours for a feedback case."""

    RED = "#ff5630"
    AMBER = "#FFAB00"
    GREEN = "#22C55E"
    BLUE = "#0099c4"
    GREY = "#C4CDD5"


@dataclass
class Case:
    """A declared case for which bespoke feedback is prescribed."""

    answer: str
    feedback: str
    is_correct: bool
    params: Any = None
    color: Optional[Color] = None
    id: str = field(default_factory=_new_id)


@dataclass(kw_only=True)
class ResponseArea:
    """Specifies the interaction when a student provides a response.

    Multiple response areas per part are allowed; if so, order is implicit.
    Use a subclass for each response type. ``grade_params`` are passed to the
    evaluation function unedited.

    Examples:
        >>> from in2lambda.api.response_area import NumericUnits, Test
        >>> area = NumericUnits(
        ...     answer="30 N",
        ...     grade_params={"rtol": 0.05},
        ...     pre_text="$F=$",
        ...     tests=[Test("30 N", True)],
        ... )
        >>> area.response_type, area.evaluation_function
        ('NUMERIC_UNITS', 'compareExpressions')
    """

    response_type: ClassVar[str]
    answer: Any = None
    evaluation_function: str
    grade_params: Optional[dict[str, Any]] = None
    pre_text: str = ""
    post_text: str = ""
    content_after: str = ""
    """Markdown shown after the box, before the next one."""
    check_button_text: str = ""
    """Replaces the label of the check button; left out of the JSON when empty."""
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

    def _config(self) -> Optional[dict[str, Any]]:
        """The response type's settings, as Lambda Feedback writes them."""
        return None

    def _grade_params(self) -> Optional[dict[str, Any]]:
        """The parameters sent to the evaluation function."""
        return self.grade_params


@dataclass(kw_only=True)
class _Maths(ResponseArea):
    answer: str = ""
    allow_handwrite: bool = True
    allow_photo: bool = True
    enable_refinement: bool = True

    def _config(self) -> Optional[dict[str, Any]]:
        return {
            "allowHandwrite": self.allow_handwrite,
            "allowPhoto": self.allow_photo,
            "enableRefinement": self.enable_refinement,
        }


@dataclass(kw_only=True)
class MathSingleLine(_Maths):
    """A single symbolic expression."""

    response_type: ClassVar[str] = "MATH_SINGLE_LINE"
    evaluation_function: str = "compareExpressions"


@dataclass(kw_only=True)
class MathMultiLines(_Maths):
    """Multiple lines of mathematical work."""

    response_type: ClassVar[str] = "MATH_MULTI_LINES"


@dataclass(kw_only=True)
class Number(ResponseArea):
    """A number."""

    response_type: ClassVar[str] = "NUMBER"
    answer: Optional[Union[int, float]] = None
    evaluation_function: str = "isSimilar"


@dataclass(kw_only=True)
class NumericUnits(ResponseArea):
    """A number with units, e.g. ``30 N``."""

    response_type: ClassVar[str] = "NUMERIC_UNITS"
    answer: str = ""
    evaluation_function: str = "compareExpressions"

    def _grade_params(self) -> Optional[dict[str, Any]]:
        # compareExpressions compares units only when told to.
        return {"physical_quantity": True, **(self.grade_params or {})}


@dataclass(kw_only=True)
class Text(ResponseArea):
    """A short piece of text."""

    response_type: ClassVar[str] = "TEXT"
    answer: str = ""


@dataclass(kw_only=True)
class Boolean(ResponseArea):
    """True or false."""

    response_type: ClassVar[str] = "BOOLEAN"
    answer: bool = False
    evaluation_function: str = "isExactEqual"


@dataclass(kw_only=True)
class MultipleChoice(ResponseArea):
    """A choice among ``options``; ``answer`` marks each option correct or not."""

    response_type: ClassVar[str] = "MULTIPLE_CHOICE"
    answer: list[bool] = field(default_factory=list)
    evaluation_function: str = "arrayEqual"
    options: list[str] = field(default_factory=list)
    single: bool = True
    randomise: bool = False

    def _config(self) -> Optional[dict[str, Any]]:
        return {
            "options": self.options,
            "randomise": self.randomise,
            "single": self.single,
        }


@dataclass(kw_only=True)
class Table(ResponseArea):
    """A grid of cells, one row per row name and one column per column name."""

    response_type: ClassVar[str] = "TABLE"
    answer: list[list[str]] = field(default_factory=list)
    evaluation_function: str = "arraySymbolicEqual"
    row_names: list[str] = field(default_factory=list)
    col_names: list[str] = field(default_factory=list)

    def _config(self) -> Optional[dict[str, Any]]:
        return {
            "rows": len(self.row_names),
            "cols": len(self.col_names),
            "rowNames": self.row_names,
            "colNames": self.col_names,
        }


@dataclass(kw_only=True)
class Matrix(ResponseArea):
    """A table, with parentheses displayed around it, with the shape of ``answer``."""

    response_type: ClassVar[str] = "MATRIX"
    answer: list[list[str]] = field(default_factory=list)
    evaluation_function: str = "arraySymbolicEqual"

    def _config(self) -> Optional[dict[str, Any]]:
        return {
            "rows": len(self.answer),
            "cols": len(self.answer[0]) if self.answer else 0,
        }


@dataclass(kw_only=True)
class Code(ResponseArea):
    """A monaco code editor."""

    response_type: ClassVar[str] = "CODE"
    answer: str = ""
    evaluation_function: str = "evaluatePython"
    language: str = "python"

    def _config(self) -> Optional[dict[str, Any]]:
        return {"language": self.language}


@dataclass(kw_only=True)
class Essay(ResponseArea):
    """Large text box."""

    response_type: ClassVar[str] = "ESSAY"
    answer: Union[str, dict[str, str]] = ""
    allow_draw: bool = False
    allow_scan: bool = False
    repeat_for_subjects: bool = False
    allow_empty_submission: bool = False

    def _config(self) -> Optional[dict[str, Any]]:
        return {
            "allowDraw": self.allow_draw,
            "allowScan": self.allow_scan,
            "repeatForSubjects": self.repeat_for_subjects,
            "allowEmptySubmission": self.allow_empty_submission,
        }


@dataclass(kw_only=True)
class Likert(ResponseArea):
    """A multiple choice with Likert scales."""

    response_type: ClassVar[str] = "LIKERT"
    answer: Union[
        list[Optional[Union[int, float]]],
        dict[str, list[Optional[Union[int, float]]]],
        None,
    ] = None
    statements: list[str] = field(default_factory=list)
    options: Optional[list[str]] = None
    repeat_for_subjects: bool = False
    allow_empty_submission: bool = False

    def _config(self) -> Optional[dict[str, Any]]:
        config: dict[str, Any] = {
            "statements": self.statements,
            "repeatForSubjects": self.repeat_for_subjects,
            "allowEmptySubmission": self.allow_empty_submission,
        }
        if self.options is not None:
            config["options"] = self.options
        return config


@dataclass(kw_only=True)
class Images(ResponseArea):
    """Upload images."""

    response_type: ClassVar[str] = "IMAGES"
    max_images: int = 3
    allowed_types: list[str] = field(
        default_factory=lambda: ["image/jpg", "image/jpeg", "image/png"]
    )
    max_size_mb: int = 10
    resize_max_side: int = 0
    """The longest side images are resized to; 0 leaves them as they are."""

    def _config(self) -> Optional[dict[str, Any]]:
        return {
            "maxImages": self.max_images,
            "allowedTypes": self.allowed_types,
            "maxSizeMb": self.max_size_mb,
            "resizeMaxSide": self.resize_max_side,
        }
