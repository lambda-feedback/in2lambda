"""Check that ``lambda-feedback`` response-area blocks are well formed.

``in2lambda wizard`` writes a fenced ``lambda-feedback`` JSON block under a
solution to configure that part's response area, and instructors may hand-edit
them. These checks run over the raw markdown (before pandoc) and report blocks
that are not valid JSON or that name something in2lambda does not recognise. Like
the delimiter checks they are advisory - conversion still goes ahead.
"""

import json
import re
from enum import Enum

from in2lambda.response_areas.registry import EVALUATION_FUNCTIONS, RESPONSE_TYPES

# A fenced block whose info string starts with "lambda-feedback"; group 1 is the
# body up to the closing fence on its own line.
_BLOCK = re.compile(r"^```lambda-feedback[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


class ResponseAreaError(Enum):
    """A problem found in a ``lambda-feedback`` fenced block.

    The value is a short human-readable message, matching
    :class:`~in2lambda.validation.delimiters.MathDelimiterError`.
    """

    INVALID_JSON = "lambda-feedback block is not valid JSON"
    NOT_AN_OBJECT = "lambda-feedback block must be a JSON object"
    UNKNOWN_EVALUATION_FUNCTION = (
        "lambda-feedback block names an evaluation function in2lambda does not know"
    )
    UNKNOWN_RESPONSE_TYPE = "lambda-feedback block names an unrecognised response type"


def response_area_checker(md_content: str) -> list[ResponseAreaError]:
    """Return one :class:`ResponseAreaError` per malformed ``lambda-feedback`` block.

    An empty list means every block (if any) is fine.

    Args:
        md_content: The markdown text to check.

    Returns:
        The problems found, in document order.

    Examples:
        >>> from in2lambda.validation.response_area import response_area_checker
        >>> response_area_checker("no response-area blocks here")
        []
        >>> broken = "```lambda-feedback\\n{ not json }\\n```\\n"
        >>> response_area_checker(broken)
        [<ResponseAreaError.INVALID_JSON: 'lambda-feedback block is not valid JSON'>]
    """
    problems: list[ResponseAreaError] = []
    for match in _BLOCK.finditer(md_content):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            problems.append(ResponseAreaError.INVALID_JSON)
            continue
        if not isinstance(data, dict):
            problems.append(ResponseAreaError.NOT_AN_OBJECT)
            continue
        function = data.get("evaluationFunction")
        if function and function not in EVALUATION_FUNCTIONS:
            problems.append(ResponseAreaError.UNKNOWN_EVALUATION_FUNCTION)
        response_type = data.get("responseType")
        if response_type and response_type not in RESPONSE_TYPES:
            problems.append(ResponseAreaError.UNKNOWN_RESPONSE_TYPE)
    return problems
