from dataclasses import dataclass, field
from typing import Union

import panflute as pf

from tex2lambda.api.question import Question


@dataclass
class Module:
    """Represents a list of questions."""

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
            >>> from tex2lambda.api.module import Module
            >>> Module().current_question
            Question(title='INVALID', parts=[], images=[], _main_text='')
            >>> module = Module()
            >>> module.add_question()
            >>> module.current_question
            Question(title='', parts=[], images=[], _main_text='')
        """
        return (
            self.questions[self._current_question_index]
            if self.questions
            else Question("INVALID")
        )

    def add_question(
        self, title: str = "", main_text: Union[pf.Element, str] = pf.Str("")
    ) -> None:
        """Inserts a new question into the module.

        Args:
            title: An optional string for the title of the question. If no title
                is provided, the question title auto-increments i.e. Question 1, 2, etc.
            main_text: An optional string or panflute element for the main question text.

        Examples:
            >>> from tex2lambda.api.module import Module
            >>> import panflute as pf
            >>> module = Module()
            >>> module.add_question("Some title", pf.Para(pf.Str("hello"), pf.Space, pf.Str("there")))
            >>> module
            Module(questions=[Question(title='Some title', parts=[], images=[], _main_text='hello there')])
            >>> module.add_question(main_text="Normal string text")
            >>> module.questions[1].main_text
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
            >>> from tex2lambda.api.module import Module
            >>> module = Module()
            >>> # Imagine adding the questions from a question file first...
            >>> module.add_question("Question 1")
            >>> module.add_question("Question 2")
            >>> # ...and then adding solutions from an answer file later
            >>> module.increment_current_question()  # Loop back to question 1
            >>> module.current_question.add_solution("Question 1 answer")
            >>> module.increment_current_question()
            >>> module.current_question.add_solution("Question 2 answer")
            >>> module.questions
            [Question(title='Question 1', parts=[Part(text='', worked_solution='Question 1 answer')], images=[], _main_text=''),\
 Question(title='Question 2', parts=[Part(text='', worked_solution='Question 2 answer')], images=[], _main_text='')]
        """
        self._current_question_index += 1
