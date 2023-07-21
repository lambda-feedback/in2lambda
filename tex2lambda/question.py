"""Contains various classes used to define how TeX questions would be processed by Lambda Feedback."""

from typing import TypedDict


class Part(TypedDict):
    """A part of a question as represented on Lambda Feedback."""

    Text: str
    Answer: str
    """Represents a worked solution."""


class Question(TypedDict):
    """A full question as represented on Lambda Feedback."""

    Title: str
    MainText: str
    Parts: list[Part]
    Images: list[str]
    """List of absolute paths to images for a question."""


class Questions:
    """A Python API for representing how questions are sectioned on Lambda Feedback."""

    def __init__(self) -> None:
        """Initialises an empty list of questions."""
        self._questions: list[Question] = []
        self._current_question_index = -1
        """The current question being modified. Defaults to -1 (the last question)"""

    @property
    def questions(self) -> list[Question]:
        """Getter method to access the questions.

        Returns:
            A list of questions.
        """
        return self._questions

    def add_question(self, text: str) -> None:
        """Initialises a new question, adding the question text as a part with no answer.

        Args:
           text: The text body of a question.
        """
        self._questions.append(
            Question(
                Title="", MainText="", Parts=[Part(Text=text, Answer="")], Images=[]
            )
        )

    def add_part(self, text: str) -> None:
        """Adds a new part to the most recently added question.

        Args:
            text: The text body of the new question part.
        """
        current_question = self._questions[self._current_question_index]

        # If there are no parts yet, take the main question text previously added as a part
        # and insert it as the header question text.
        if current_question["MainText"] == "":
            current_question["MainText"] = current_question["Parts"][0]["Text"]
            current_question["Parts"] = []

        current_question["Parts"].append(Part(Text=text, Answer=""))

    def add_image(self, location: str) -> None:
        """Indicates that the most recently added question requires a given image.

        Args:
            location: The absolute path to an image.
        """
        current_question = self._questions[self._current_question_index]
        current_question["Images"].append(location)

    def add_solution_all_parts(self, text: str) -> None:
        """Adds a solution to all parts of a question.

        Used if the original TeX file doesn't break down its solution for the given parts.

        Args:
            text: The text body of the solution.
        """
        current_question = self._questions[self._current_question_index]

        for part in current_question["Parts"]:
            part["Answer"] = text

    def add_solution_part(self, text: str) -> None:
        """Adds a solution to the first question part lacking a solution.

        If all parts already have a solution, no changes are made.

        Args:
            text: The text body of the solution.
        """
        current_question = self._questions[self._current_question_index]

        for part in current_question["Parts"]:
            if not part["Answer"]:
                part["Answer"] = text
                break

    def increment_current_question(self) -> None:
        """Manually overrides the current question being modified.

        The default (-1) indicates the last question added. Incrementing for the
        first time sets to 0 i.e. the first question.

        The is useful if adding question text first and answers later.
        """
        self._current_question_index += 1
