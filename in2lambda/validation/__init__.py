"""Pre-flight checks for the ``#``/``##`` and ``$``/``$$`` markdown delimiters.

The markdown that in2lambda converts - however it was produced - is a shared
contract with Lambda Feedback. These checks catch structural mistakes in that
markdown, currently unbalanced or misplaced math delimiters, before it is
converted.
"""

from in2lambda.validation.delimiters import MathDelimiterError, math_delimiter_checker

__all__ = ["MathDelimiterError", "math_delimiter_checker", "check_markdown"]


def check_markdown(md_content: str) -> list[MathDelimiterError]:
    """Run every markdown check and return the problems found.

    Args:
        md_content: The markdown text to validate.

    Returns:
        A list of :class:`MathDelimiterError` members, one per problem found.
        An empty list means the markdown passed every check.

    Examples:
        >>> from in2lambda.validation import check_markdown
        >>> check_markdown("Inline $x = y$ is fine.")
        []
        >>> check_markdown("Unbalanced $x = y")
        [<MathDelimiterError.MISSING_CLOSING_SINGLE_DOLLAR: 'unclosed inline $ ... $'>]
    """
    problems: list[MathDelimiterError] = []

    result = math_delimiter_checker(md_content)
    if result is not MathDelimiterError.PASSED:
        problems.append(result)

    return problems
