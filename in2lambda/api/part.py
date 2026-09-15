"""A part of a question."""

from dataclasses import dataclass, field

from in2lambda.api.response_area import ResponseArea


@dataclass
class Part:
    """A part of a question as represented on Lambda Feedback.

    ``worked_solution`` is markdown; a line holding only ``---`` (or ``***``) splits it
    into the steps students go through one at a time. ``answer`` is the final answer
    shown to students, and ``response_areas`` the boxes, in order, that mark what they
    type.
    """

    text: str = ""
    worked_solution: str = ""
    answer: str = ""
    response_areas: list[ResponseArea] = field(default_factory=list)
