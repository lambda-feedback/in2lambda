"""A response area: where a student answers, and how that answer is marked.

A :class:`ResponseArea` bundles the four things Lambda Feedback needs to
auto-mark one input on a question part:

* ``response_type`` - the kind of input widget (``EXPRESSION``, ``NUMBER``,
  ``BOOLEAN``, ``TEXT``, ``ESSAY``, ``CODE``, ``NUMERIC_UNITS``, ...),
* ``answer`` - the reference answer, as a string,
* ``evaluation_function`` - which evaluation function grades the response
  (see :data:`in2lambda.response_areas.EVALUATION_FUNCTIONS`),
* ``grade_params`` - that function's parameters.

:mod:`in2lambda.json_convert` turns each one into an entry in a part's
``responseAreas`` array on import.
"""

from dataclasses import dataclass, field


@dataclass
class ResponseArea:
    """One markable input on a question part.

    Examples:
        >>> from in2lambda.api.response_area import ResponseArea
        >>> ResponseArea("EXPRESSION", "pi*d", "compareExpressions", {"rtol": 0.01})
        ResponseArea(response_type='EXPRESSION', answer='pi*d', \
evaluation_function='compareExpressions', grade_params={'rtol': 0.01}, config={}, \
pre_response_text='', post_response_text='')
    """

    response_type: str
    answer: str
    evaluation_function: str
    grade_params: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    pre_response_text: str = ""
    post_response_text: str = ""
