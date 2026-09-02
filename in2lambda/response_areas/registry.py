"""in2lambda's local model of Lambda Feedback's evaluation functions.

This mirrors
https://docs.lambdafeedback.com/teacher/reference/evaluation_functions/ and is
the single source of truth for:

* which evaluation functions ``in2lambda wizard`` may propose,
* which response-area input types each one pairs with,
* the parameters the interactive confirmation step offers.

Parameter lists for ``compareExpressions`` and ``comparePhysicalQuantities`` are
complete; the others carry their common parameters plus a ``TODO`` pointing at
the per-function docs page. Nothing here is *enforced* against Lambda Feedback -
:mod:`in2lambda.json_convert` passes unknown functions and parameters through
untouched, so a newer function still works, it just is not offered in the menu.
"""

from dataclasses import dataclass
from typing import Optional

#: Response-area input types (``response.responseInput.responseType`` on import).
#: ``CODE`` and ``ESSAY`` are confirmed from exported questions; the rest are
#: from the docs and should be checked against a real export.
RESPONSE_TYPES: tuple[str, ...] = (
    "EXPRESSION",
    "NUMBER",
    "NUMERIC_UNITS",
    "BOOLEAN",
    "TEXT",
    "ESSAY",
    "CODE",
    "MATRIX",
    "TABLE",
    "MULTIPLE_CHOICE",
)


@dataclass(frozen=True)
class ParamSpec:
    """One parameter of an evaluation function.

    ``type`` is one of ``"number"``, ``"boolean"``, ``"string"`` or ``"json"``
    and only drives how the interactive prompt parses what the instructor types.
    """

    name: str
    type: str
    default: object
    help: str


@dataclass(frozen=True)
class EvaluationFunctionSpec:
    """An evaluation function: its name, the inputs it grades, its parameters."""

    name: str
    response_types: tuple[str, ...]
    params: tuple[ParamSpec, ...] = ()
    answer_hint: str = ""


def _f(
    name: str,
    response_types: tuple[str, ...],
    *params: ParamSpec,
    answer_hint: str = ""
) -> EvaluationFunctionSpec:
    return EvaluationFunctionSpec(name, response_types, tuple(params), answer_hint)


# --- compareExpressions: parameters complete, from the docs page ---------------
_COMPARE_EXPRESSIONS = _f(
    "compareExpressions",
    ("EXPRESSION", "MATH_SINGLE_LINE", "MATH_MULTI_LINE"),
    ParamSpec(
        "absolute_tolerance",
        "number",
        0,
        "abs tolerance for numeric answers (alias: atol)",
    ),
    ParamSpec(
        "relative_tolerance",
        "number",
        0,
        "relative tolerance for numeric answers (alias: rtol)",
    ),
    ParamSpec("complexNumbers", "boolean", False, "treat I as the imaginary unit"),
    ParamSpec(
        "convention",
        "string",
        "equal_precedence",
        "equal_precedence | implicit_higher_precedence",
    ),
    ParamSpec(
        "criteria",
        "string",
        "answer=response",
        "custom comparison using keywords answer / response",
    ),
    ParamSpec(
        "elementary_functions",
        "boolean",
        False,
        "reserve sin, cos, exp, sqrt, ... as names",
    ),
    ParamSpec(
        "multiple_answers_criteria",
        "string",
        "all",
        "how +/- answers must match: all | all_responses | all_answers",
    ),
    ParamSpec(
        "physical_quantity",
        "boolean",
        False,
        "interpret expressions as physical quantities with units",
    ),
    ParamSpec(
        "strictness",
        "string",
        "natural",
        "physical-quantity parsing: strict | natural | legacy",
    ),
    ParamSpec(
        "units_string",
        "string",
        "SI common imperial",
        "permitted unit sets (space-separated)",
    ),
    ParamSpec("specialFunctions", "boolean", False, "enable beta, gamma, zeta"),
    ParamSpec(
        "strict_syntax", "boolean", False, "require explicit * and / and ** for powers"
    ),
    ParamSpec(
        "symbol_assumptions", "string", "", "e.g. ('a','positive') ('b','positive')"
    ),
    answer_hint="a symbolic expression, e.g. 'pi*d' or '1/2*m*v**2'",
)

# --- comparePhysicalQuantities: parameters complete, from the docs page --------
_COMPARE_PHYSICAL_QUANTITIES = _f(
    "comparePhysicalQuantities",
    ("NUMERIC_UNITS", "EXPRESSION"),
    ParamSpec(
        "elementary_functions", "boolean", False, "reserve common function names"
    ),
    ParamSpec(
        "substitutions",
        "string",
        "",
        "substitutions applied to answer and response first",
    ),
    ParamSpec("quantities", "string", "", "quantities usable in answer and response"),
    ParamSpec(
        "strict_syntax",
        "boolean",
        True,
        "require * or / between parts and ** for powers",
    ),
    ParamSpec("rtol", "number", 1e-12, "max relative error"),
    ParamSpec("atol", "number", 0, "max absolute error"),
    ParamSpec(
        "comparison",
        "string",
        "expression",
        "expression | expressionExact | dimensions | buckinghamPi",
    ),
    ParamSpec("custom_feedback", "json", {}, "feedback messages keyed by tag"),
    answer_hint="a quantity with units, e.g. '9.81 metre/second**2'",
)

# --- the rest: common params + TODO to confirm from the per-function docs ------
# https://docs.lambdafeedback.com/user_eval_function_docs/<name>/
_SYMBOLIC_EQUAL = _f(
    "symbolicEqual",
    ("EXPRESSION", "MATH_SINGLE_LINE", "MATH_MULTI_LINE"),
    ParamSpec("strict_syntax", "boolean", True, "require * / and ** for powers"),
    ParamSpec(
        "elementary_functions", "boolean", False, "reserve common function names"
    ),
    answer_hint="a symbolic expression",
)
_IS_EXACT_EQUAL = _f(
    "isExactEqual",
    ("EXPRESSION", "NUMBER", "TEXT"),
    answer_hint="the exact string the response must match",
)
_COMPARE_BOOLEAN = _f(
    "compareBoolean",
    ("BOOLEAN",),
    answer_hint="'true' or 'false'",
)
_COMPARE_SETS = _f(
    "compareSets",
    ("TEXT", "TABLE"),
    ParamSpec("elements", "json", [], "the set the response is compared against"),
    answer_hint="a comma-separated set, e.g. '1, 2, 3'",
)
_ARRAY_EQUAL = _f(
    "arrayEqual",
    ("MATRIX", "TABLE"),
    answer_hint="rows of values",
)
_ARRAY_SYMBOLIC_EQUAL = _f(
    "arraySymbolicEqual",
    ("MATRIX", "TABLE"),
    ParamSpec("strict_syntax", "boolean", True, "require * / and ** for powers"),
    answer_hint="rows of symbolic expressions",
)
_SHORT_TEXT_ANSWER = _f(
    "shortTextAnswer",
    ("TEXT",),
    ParamSpec("case_sensitive", "boolean", False, "match case exactly"),
    ParamSpec("strip", "boolean", True, "ignore leading/trailing whitespace"),
    answer_hint="the expected short text",
)
_IS_SIMILAR = _f(
    "isSimilar",
    ("TEXT", "NUMBER", "ESSAY"),
    ParamSpec("threshold", "number", 0.8, "similarity score required to be correct"),
    answer_hint="a reference answer to compare semantically",
)
_LANG_MODELS = _f(
    "langModels",
    ("ESSAY", "TEXT", "MILKDOWN"),
    ParamSpec("model", "string", "openai/gpt-4o-mini", "model slug"),
    ParamSpec("context", "string", "", "extra marking context for the model"),
    ParamSpec(
        "feedback_guidance", "string", "", "how the model should phrase feedback"
    ),
    ParamSpec(
        "correctness_decision",
        "string",
        "",
        "rule the model uses to decide correct/incorrect ({{answer}} allowed)",
    ),
    answer_hint="a model answer; referenced as {{answer}} in the prompts",
)
_GCSE_ENGLISH = _f(
    "GCSEenglish", ("ESSAY",), answer_hint="a model answer / mark scheme"
)
_SURVEY = _f(
    "survey", ("MULTIPLE_CHOICE", "LIKERT"), answer_hint="(surveys are not marked)"
)
_BUCKINGHAM_PI = _f(
    "buckinghamPiTheorem",
    ("EXPRESSION",),
    answer_hint="the dimensionless groups, e.g. 'U*L/nu'",
)

# --- seen in exported questions but not on the public reference page ----------
_EVALUATE_PYTHON = _f(
    "evaluatePython",
    ("CODE",),
    ParamSpec("mode", "string", "unit_test", "unit_test | io_test | demo"),
    ParamSpec(
        "use_answer_as_test_code",
        "boolean",
        True,
        "unit_test: answer is the pytest code",
    ),
    ParamSpec(
        "use_answer_as_expected_output",
        "boolean",
        True,
        "io_test: answer is the expected stdout",
    ),
    ParamSpec("tests", "json", [], "io_test: list of {input, hidden}"),
    answer_hint="Python: the test code (unit_test) or expected output (io_test)",
)
_CALL_LLM = _f(
    "callLLM",
    ("ESSAY", "TEXT"),
    ParamSpec("model", "string", "openai/gpt-4o-mini", "model slug"),
    ParamSpec("context", "string", "", "extra marking context"),
    ParamSpec("feedback_guidance", "string", "", "how feedback should be phrased"),
    ParamSpec(
        "correctness_decision",
        "string",
        "",
        "correct/incorrect rule ({{answer}} allowed)",
    ),
    answer_hint="a model answer; referenced as {{answer}} in the prompts",
)

EVALUATION_FUNCTIONS: dict[str, EvaluationFunctionSpec] = {
    spec.name: spec
    for spec in (
        _COMPARE_EXPRESSIONS,
        _SYMBOLIC_EQUAL,
        _IS_EXACT_EQUAL,
        _COMPARE_PHYSICAL_QUANTITIES,
        _COMPARE_BOOLEAN,
        _COMPARE_SETS,
        _ARRAY_EQUAL,
        _ARRAY_SYMBOLIC_EQUAL,
        _SHORT_TEXT_ANSWER,
        _IS_SIMILAR,
        _LANG_MODELS,
        _GCSE_ENGLISH,
        _SURVEY,
        _BUCKINGHAM_PI,
        _EVALUATE_PYTHON,
        _CALL_LLM,
    )
}


def get(name: str) -> Optional[EvaluationFunctionSpec]:
    """Return the spec for ``name``, or ``None`` if it is not in the registry.

    Examples:
        >>> from in2lambda.response_areas.registry import get
        >>> get("compareExpressions").response_types[0]
        'EXPRESSION'
        >>> get("not-a-function") is None
        True
    """
    return EVALUATION_FUNCTIONS.get(name)


def function_names() -> list[str]:
    """Every evaluation-function name in the registry, in registration order.

    Examples:
        >>> from in2lambda.response_areas.registry import function_names
        >>> "compareExpressions" in function_names()
        True
    """
    return list(EVALUATION_FUNCTIONS)


def functions_for(response_type: str) -> list[str]:
    """Names of the evaluation functions that pair with ``response_type``.

    Examples:
        >>> from in2lambda.response_areas.registry import functions_for
        >>> functions_for("BOOLEAN")
        ['compareBoolean']
    """
    return [
        name
        for name, spec in EVALUATION_FUNCTIONS.items()
        if response_type in spec.response_types
    ]
