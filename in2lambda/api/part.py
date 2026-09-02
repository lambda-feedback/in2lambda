"""A part of a question."""

from dataclasses import dataclass, field

from in2lambda.api.response_area import ResponseArea


@dataclass
class Part:
    """A part of a question as represented on Lambda Feedback."""

    text: str = ""
    worked_solution: str = ""
    # Kept out of repr so the many doctests that assert on Part(...) / Question(...)
    # output stay valid; response areas are inspected explicitly where they matter.
    response_areas: list[ResponseArea] = field(default_factory=list, repr=False)
