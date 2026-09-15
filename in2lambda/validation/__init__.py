"""Pre-flight checks for the markdown that flows through in2lambda.

The markdown produced by the wizard (and hand-written by users) is the shared
contract between the wizard, the ``Markdown`` filter and Lambda Feedback. These
checks catch structural mistakes - currently unbalanced/misplaced math
delimiters - before the markdown is converted.
"""

from in2lambda.validation.delimiters import (
    MathDelimiterError,
    MathDelimiterProblem,
    math_delimiter_checker,
)

__all__ = [
    "MathDelimiterError",
    "MathDelimiterProblem",
    "math_delimiter_checker",
    "check_markdown",
]


def check_markdown(md_content: str) -> list[MathDelimiterProblem]:
    """Run every markdown check and return the problems found.

    Args:
        md_content: The markdown text to validate.

    Returns:
        A list of :class:`MathDelimiterProblem`, one per problem found.
        An empty list means the markdown passed every check.

    Examples:
        >>> from in2lambda.validation import check_markdown
        >>> check_markdown("Inline $x = y$ is fine.")
        []
        >>> check_markdown("Unbalanced $x = y")
        [MathDelimiterProblem(line=1, error=<MathDelimiterError.MISSING_CLOSING_SINGLE_DOLLAR: 'unclosed inline $ ... $'>)]
    """
    return math_delimiter_checker(md_content)
