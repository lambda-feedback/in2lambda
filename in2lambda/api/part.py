"""A part of a question."""

from dataclasses import dataclass, field

from in2lambda.api.response_area import ResponseArea


@dataclass
class Branch:
    """A (titled) branch of a structured tutorial or worked solution, which may branch further."""

    title: str
    content: str
    branches: list["Branch"] = field(default_factory=list)


@dataclass
class Part:
    """A part of a question as represented on Lambda Feedback.

    Markdown content for the question and supporting materials. Note that in ``tutorial`` and ``worked_solution`` fields, steps can by separated by a line with only ``---`` (or ``***``).
    """

    content: str = ""
    response_areas: list[ResponseArea] = field(default_factory=list)
    tutorial: str = ""
    tutorial_branches: list[Branch] = field(default_factory=list)
    answer: str = ""
    worked_solution: str = ""
    worked_solution_branches: list[Branch] = field(default_factory=list)
