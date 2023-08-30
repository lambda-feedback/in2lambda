"""A part of a question."""

from dataclasses import dataclass


@dataclass
class Part:
    """A part of a question as represented on Lambda Feedback."""

    text: str = ""
    worked_solution: str = ""
