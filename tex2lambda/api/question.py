"""A full question with optional parts that's contained in a module."""

from dataclasses import dataclass, field
from typing import Union

import panflute as pf

from tex2lambda.api.part import Part


@dataclass
class Question:
    """A full question as represented on Lambda Feedback.

    Each question has a title and is composed of a list of parts.

    Examples:
        >>> from tex2lambda.api.question import Question
        >>> Question(title="Some title", _main_text="Some text")
        Question(title='Some title', parts=[], images=[], _main_text='Some text')
    """

    title: str = ""

    parts: list[Part] = field(default_factory=list)
    images: list[str] = field(default_factory=list)

    _main_text: str = ""
    _last_part: dict[str, int] = field(
        default_factory=lambda: {"solution": 0, "text": 0}, repr=False
    )
    """Keeps track of the last question part that contains a solution /
    text."""

    @property
    def main_text(self) -> str:
        """Main top-level question text."""
        return self._main_text

    @main_text.setter
    def main_text(self, value: Union[pf.Element, str]) -> None:
        r"""Appends to the top-level main text, which starts off as an empty string.

        Args:
            value: A panflute element or string denoting what to append to the main text.

        Examples:
            >>> from tex2lambda.api.question import Question
            >>> question = Question()
            >>> question.main_text = "hello"
            >>> question.main_text = "there"
            >>> question.main_text
            'hello\nthere'
        """
        text_value = value if isinstance(value, str) else pf.stringify(value, False)
        if self._main_text:
            self._main_text += "\n"
        self._main_text += text_value

    def add_solution(self, elem: Union[pf.Element, str]) -> None:
        """Adds a worked solution to all question parts without one, or inserts a new empty part with the solution if all parts already have a solution.

        Args:
            elem: A string or panflute element denoting a worked solution.

        Examples:
            >>> from tex2lambda.api.question import Question
            >>> question = Question()
            >>> question.add_part_text("part a")
            >>> question.add_solution("part a solution")
            >>> question
            Question(title='', parts=[Part(text='part a', worked_solution='part a solution')], images=[], _main_text='')
            >>> question.add_part_text("part b")
            >>> question.add_part_text("part c")
            >>> question.add_solution("Solution for b")
            >>> # Note that since c doesn't have a solution, it's set to b's solution
            >>> question
            Question(title='', parts=[Part(text='part a', worked_solution='part a solution'), \
Part(text='part b', worked_solution='Solution for b'), \
Part(text='part c', worked_solution='Solution for b')], images=[], _main_text='')
            >>> question.add_solution("We now have a solution for c!")
            >>> question
            Question(title='', parts=[Part(text='part a', worked_solution='part a solution'), \
Part(text='part b', worked_solution='Solution for b'), \
Part(text='part c', worked_solution='We now have a solution for c!')], images=[], _main_text='')
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
            >>> from tex2lambda.api.question import Question
            >>> question = Question()
            >>> question.add_part_text("part a")
            >>> question.add_solution("part a solution")
            >>> question
            Question(title='', parts=[Part(text='part a', worked_solution='part a solution')], images=[], _main_text='')
            >>> # Supports adding the answer first.
            >>> question.add_solution("part b solution")
            >>> question.add_part_text("part b")
            >>> question
            Question(title='', parts=[Part(text='part a', worked_solution='part a solution'), \
Part(text='part b', worked_solution='part b solution')], images=[], _main_text='')
        """
        elem_text = elem if isinstance(elem, str) else pf.stringify(elem)

        if len(self.parts) == self._last_part["text"]:
            self.parts.append(Part(text=elem_text))
        else:
            self.parts[self._last_part["text"]].text = elem_text

        self._last_part["text"] += 1
