"""Something wrong with a question set, and where in it to look."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """Something in2lambda can tell Lambda Feedback will refuse or render wrongly.

    ``location`` names the question, part and field to go and look at; ``message``
    says what is wrong with it.

    Examples:
        >>> from in2lambda.api.problem import Problem
        >>> print(Problem('Question 1 "Drag", part (a), answer box 1', "no option is marked correct"))
        Question 1 "Drag", part (a), answer box 1: no option is marked correct
    """

    location: str
    message: str

    def __str__(self) -> str:
        """One line for the command line: ``<location>: <message>``."""
        return f"{self.location}: {self.message}"
