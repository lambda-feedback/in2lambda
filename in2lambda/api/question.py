"""A full question with optional parts that's contained in a set."""

from dataclasses import dataclass, field
from typing import Optional, Union

import panflute as pf

from in2lambda import defaults
from in2lambda.api.part import Part
from in2lambda.defaults import UNSET


@dataclass
class Question:
    """A full question as represented on Lambda Feedback.

    Each question has a title and is composed of a list of parts.

    It also carries the settings Lambda Feedback keeps per question.

    Examples:
        >>> from in2lambda.api.question import Question
        >>> Question(title="Some title", master_content="Some text")
        Question(title='Some title', parts=[], images=[], master_content='Some text')
    """

    title: str = ""

    parts: list[Part] = field(default_factory=list)
    images: list[str] = field(default_factory=list)

    # Use getter/setter methods for master_content without exposing private attribute.
    # See https://stackoverflow.com/a/61480946
    master_content: str = ""
    _master_content: str = field(init=False, repr=False, default="")

    _last_part: dict[str, int] = field(
        default_factory=lambda: {"solution": 0, "text": 0}, repr=False
    )
    """Keeps track of the last question part that contains a solution /
    text."""

    # The settings below are left out of the repr, so that printing a question shows its
    # content rather than nine lines of configuration. Those set to UNSET default to
    # what in2lambda's defaults.toml gives them.

    # The skill level may be an int as well as a float, because Lambda Feedback writes
    # its exports in JavaScript, which writes the levels 0.0 and 1.0 as 0 and 1.
    skill: Optional[Union[int, float]] = field(default=None, repr=False)
    guidance: Optional[str] = field(default=None, repr=False)
    duration_lower_bound: Optional[int] = field(default=None, repr=False)
    duration_upper_bound: Optional[int] = field(default=None, repr=False)
    publish: bool = field(default=UNSET, repr=False)
    display_final_answer: bool = field(default=UNSET, repr=False)
    display_worked_solution: bool = field(default=UNSET, repr=False)
    display_structured_tutorial: bool = field(default=UNSET, repr=False)
    display_chatbot: bool = field(default=UNSET, repr=False)

    def __post_init__(self) -> None:
        """Gives each setting left unset its default."""
        defaults.fill(self, "question")

    @property
    def master_content(self) -> str:
        r"""Main top-level question text.

        Setting the attribute multiple times appends to the current value with a newline.
        This allows question text to be dynamically appended.

        Examples:
            >>> from in2lambda.api.question import Question
            >>> question = Question()
            >>> question.master_content = "hello"
            >>> question.master_content = "there"
            >>> question.master_content
            'hello\nthere'
        """
        return self._master_content

    @master_content.setter
    def master_content(self, value: Union[pf.Element, str, property]) -> None:
        r"""Appends to the top-level main text, which starts off as an empty string.

        Args:
            value: A panflute element or string denoting what to append to the main text.

        See example in master_content property.
        """
        # Converts the inputted value into a string, stored in text_value
        match value:
            case str():
                text_value = value
            case property():
                # Use default value when no value set at initialisation.
                # See https://stackoverflow.com/a/61480946
                text_value = self.master_content
            case pf.Element():
                text_value = pf.stringify(value, False)

        if self._master_content:
            self._master_content += "\n"
        self._master_content += text_value

    def add_solution(self, elem: Union[pf.Element, str]) -> None:
        """Adds a worked solution to all question parts without one, or inserts a new empty part with the solution if all parts already have a solution.

        Args:
            elem: A string or panflute element denoting a worked solution.

        Examples:
            >>> from in2lambda.api.question import Question
            >>> question = Question()
            >>> question.add_part_text("part a")
            >>> question.add_solution("part a solution")
            >>> question
            Question(title='', parts=[Part(content='part a', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='part a solution', worked_solution_branches=[])], images=[], master_content='')
            >>> question.add_part_text("part b")
            >>> question.add_part_text("part c")
            >>> question.add_solution("Solution for b")
            >>> # Note that since c doesn't have a solution, it's set to b's solution
            >>> question
            Question(title='', parts=[Part(content='part a', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='part a solution', worked_solution_branches=[]), \
Part(content='part b', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='Solution for b', worked_solution_branches=[]), \
Part(content='part c', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='Solution for b', worked_solution_branches=[])], images=[], master_content='')
            >>> question.add_solution("We now have a solution for c!")
            >>> question
            Question(title='', parts=[Part(content='part a', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='part a solution', worked_solution_branches=[]), \
Part(content='part b', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='Solution for b', worked_solution_branches=[]), \
Part(content='part c', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='We now have a solution for c!', worked_solution_branches=[])], images=[], master_content='')
        """
        elem_text = elem if isinstance(elem, str) else pf.stringify(elem)

        # If all parts have a distinct solution, add an empty part with the solution
        # This is useful if the solutions arrive before the part text in the filter.
        if len(self.parts) == self._last_part["solution"]:
            self.parts.append(Part(worked_solution=elem_text))

        # If there are more parts than solutions, set all parts with no answer to this one.
        # This is useful if a question has parts but the answer doesn't split by part.
        elif len(self.parts) > self._last_part["solution"]:
            for part in self.parts[self._last_part["solution"] :]:
                part.worked_solution = elem_text

        self._last_part["solution"] += 1

    def add_part_text(self, elem: Union[pf.Element, str]) -> None:
        """Either adds a new part with the given text or modifies the first part with no text.

        Args:
            elem: A string or panflute element denoting what the part text should be.

        Examples:
            >>> from in2lambda.api.question import Question
            >>> question = Question()
            >>> question.add_part_text("part a")
            >>> question.add_solution("part a solution")
            >>> question
            Question(title='', parts=[Part(content='part a', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='part a solution', worked_solution_branches=[])], images=[], master_content='')
            >>> # Supports adding the answer first.
            >>> question.add_solution("part b solution")
            >>> question.add_part_text("part b")
            >>> question
            Question(title='', parts=[Part(content='part a', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='part a solution', worked_solution_branches=[]), \
Part(content='part b', response_areas=[], tutorial='', tutorial_branches=[], answer='', worked_solution='part b solution', worked_solution_branches=[])], images=[], master_content='')
        """
        elem_text = elem if isinstance(elem, str) else pf.stringify(elem)

        if len(self.parts) == self._last_part["text"]:
            self.parts.append(Part(content=elem_text))
        else:
            self.parts[self._last_part["text"]].content = elem_text

        self._last_part["text"] += 1
