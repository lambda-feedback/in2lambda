"""Lambda Feedback evaluation functions and response-area defaults.

:data:`EVALUATION_FUNCTIONS` is in2lambda's model of the functions documented at
https://docs.lambdafeedback.com/teacher/reference/evaluation_functions/ ; it
drives what ``in2lambda wizard`` proposes and offers in its confirmation prompt.
"""

from in2lambda.response_areas.defaults import default_config
from in2lambda.response_areas.registry import (
    EVALUATION_FUNCTIONS,
    RESPONSE_TYPES,
    EvaluationFunctionSpec,
    ParamSpec,
    function_names,
    functions_for,
    get,
)

__all__ = [
    "EVALUATION_FUNCTIONS",
    "RESPONSE_TYPES",
    "EvaluationFunctionSpec",
    "ParamSpec",
    "function_names",
    "functions_for",
    "get",
    "default_config",
]
