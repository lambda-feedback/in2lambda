"""Represents a list of questions."""

from dataclasses import dataclass, field
from typing import Union

import panflute as pf

from in2lambda.api.question import Question


@dataclass
class Set:
    """Represents a list of questions."""

    _name: str = field(default="set")
    _description: str = field(default="")

    questions: list[Question] = field(default_factory=list)
    _current_question_index = -1

    @property
    def current_question(self) -> Question:
        """The current question being modified, or Question("INVALID") if there are no questions.

        The reasoning behind returning Question("INVALID") is in case filter logic is being applied
        on text before the first question (e.g. intro paragraphs). In that case, there is no effect.

        Returns:
            The current question or Question("INVALID") if there are no questions.

        Examples:
            >>> from in2lambda.api.set import Set
            >>> Set().current_question
            Question(title='INVALID', parts=[], images=[], main_text='')
            >>> s = Set()
            >>> s.add_question()
            >>> s.current_question
            Question(title='', parts=[], images=[], main_text='')
        """
        return (
            self.questions[self._current_question_index]
            if self.questions
            else Question("INVALID")
        )

    def add_question(
        self, title: str = "", main_text: Union[pf.Element, str] = pf.Str("")
    ) -> None:
        """Inserts a new question into the set.

        Args:
            title: An optional string for the title of the question. If no title
                is provided, the question title auto-increments i.e. Question 1, 2, etc.
            main_text: An optional string or panflute element for the main question text.

        Examples:
            >>> from in2lambda.api.set import Set
            >>> import panflute as pf
            >>> s = Set()
            >>> s.add_question("Some title", pf.Para(pf.Str("hello"), pf.Space, pf.Str("there")))
            >>> s
            Set(questions=[Question(title='Some title', parts=[], images=[], main_text='hello there')])
            >>> s.add_question(main_text="Normal string text")
            >>> s.questions[1].main_text
            'Normal string text'
        """
        question = Question(title=title)
        question.main_text = main_text
        self.questions.append(question)

    def increment_current_question(self) -> None:
        """Manually overrides the current question being modified.

        The default (-1) indicates the last question added. Incrementing for the
        first time sets to 0 i.e. the first question.

        The is useful if adding question text first and answers later.

        Examples:
            >>> from in2lambda.api.set import Set
            >>> s = Set()
            >>> # Imagine adding the questions from a question file first...
            >>> s.add_question("Question 1")
            >>> s.add_question("Question 2")
            >>> # ...and then adding solutions from an answer file later
            >>> s.increment_current_question()  # Loop back to question 1
            >>> s.current_question.add_solution("Question 1 answer")
            >>> s.increment_current_question()
            >>> s.current_question.add_solution("Question 2 answer")
            >>> s.questions
            [Question(title='Question 1', parts=[Part(text='', worked_solution='Question 1 answer')], images=[], main_text=''),\
 Question(title='Question 2', parts=[Part(text='', worked_solution='Question 2 answer')], images=[], main_text='')]
        """
        self._current_question_index += 1

    def to_json(self, output_dir: str) -> None:
        """Turns this set into Lambda Feedback JSON/ZIP files.

        WARNING: This will overwrite any existing files in the directory.

        Args:
            output_dir: Where to output the final Lambda Feedback JSON/ZIP files.

        Examples:
            >>> import tempfile
            >>> import os
            >>> import json
            >>> # Create a set with two questions
            >>> s = Set()
            >>> s.add_question("Question 1")
            >>> s.add_question("Question 2")
            >>> with tempfile.TemporaryDirectory() as temp_dir:
            ...     # Write the JSON files to the temporary directory
            ...     s.to_json(temp_dir)
            ...     # Check the contents of the directory
            ...     sorted(os.listdir(temp_dir))
            ...     # Check the contents of the set directory
            ...     sorted(os.listdir(f"{temp_dir}/set"))
            ...     # Check the title of the first question
            ...     with open(f"{temp_dir}/set/question_1.json") as file:
            ...         print(f"Question 1's title: {json.load(file)['title']}")
            ['set', 'set.zip']
            ['media', 'question_1.json', 'question_2.json']
            Question 1's title: Question 1

        """

        from in2lambda.json_convert import json_convert

        json_convert.main(self, output_dir)

    def set_name(self, name: str) -> None:
        """Sets the name of the set.

        Args:
            name: The name to set for the set.

        Examples:
            >>> from in2lambda.api.set import Set
            >>> s = Set()
            >>> s.set_name("My Question Set")
            >>> s._name
            'My Question Set'
        """
        self._name = name

    def set_description(self, description: str) -> None:
        """Sets the description of the set.

        Args:
            description: The description to set for the set.

        Examples:
            >>> from in2lambda.api.set import Set
            >>> s = Set()
            >>> s.set_description("This is my question set.")
            >>> s._description
            'This is my question set.'
        """
        self._description = description
