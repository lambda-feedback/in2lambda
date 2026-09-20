"""Checks that ``$ ... $`` and ``$$ ... $$`` math delimiters are balanced and placed correctly.

KaTeX, and so Lambda Feedback, reads inline maths wrapped in single dollar signs
on one line, and display maths wrapped in ``$$``, with each ``$$`` alone on a line
of its own. :func:`math_delimiter_checker` reads markdown character by character and
reports the first delimiter mistake it finds.
"""

from enum import Enum


class MathDelimiterError(Enum):
    """The outcome of :func:`math_delimiter_checker`.

    ``PASSED`` means the checker found no mistake. Every other member names one
    delimiter mistake. The value is a short message for the command line.
    """

    PASSED = "ok"
    MISSING_NEWLINE_BEFORE_OPENING_DISPLAY = "opening $$ must start its own line"
    MISSING_NEWLINE_AFTER_OPENING_DISPLAY = "opening $$ must be followed by a newline"
    DOUBLE_DOLLAR_INSTEAD_OF_CLOSING_SINGLE = "inline $ ... $ closed with $$"
    MISSING_CLOSING_DOUBLE_INSTEAD_OF_SINGLE = (
        "display $$ ... $$ closed with a single $"
    )
    MISSING_NEWLINE_BEFORE_CLOSING_DISPLAY = "closing $$ must start its own line"
    MISSING_NEWLINE_AFTER_CLOSING_DISPLAY = "closing $$ must be followed by a newline"
    INVALID_NEWLINE_INSIDE_INLINE = "newline inside an inline $ ... $ expression"
    MISSING_CLOSING_SINGLE_DOLLAR = "unclosed inline $ ... $"
    MISSING_CLOSING_DOUBLE_DOLLAR = "unclosed display $$ ... $$"


def math_delimiter_checker(md_content: str) -> MathDelimiterError:
    r"""Scans markdown for the first math-delimiter mistake.

    ``\$`` is a literal dollar sign and not a delimiter.

    Args:
        md_content: The markdown text to check.

    Returns:
        ``MathDelimiterError.PASSED`` where the delimiters are well formed, and
        otherwise the member naming the first mistake found.

    Examples:
        >>> from in2lambda.validation.delimiters import math_delimiter_checker
        >>> math_delimiter_checker("An inline $x = y$ expression.")
        <MathDelimiterError.PASSED: 'ok'>
        >>> math_delimiter_checker("Display:\n$$\nx = y\n$$")
        <MathDelimiterError.PASSED: 'ok'>
        >>> math_delimiter_checker("This costs \\$5, no math here.")
        <MathDelimiterError.PASSED: 'ok'>
        >>> math_delimiter_checker("Broken $x = y")
        <MathDelimiterError.MISSING_CLOSING_SINGLE_DOLLAR: 'unclosed inline $ ... $'>
    """
    # False inside a maths expression, while its closing delimiter is still to come.
    expect_open_delimiter = True
    # Inside an expression, whether it opened with a single "$" (inline) or "$$" (display).
    expect_single_dollar = True

    idx = 0
    while idx < len(md_content):
        prev_character = md_content[idx - 1] if idx > 0 else None
        character = md_content[idx]
        next_character = md_content[idx + 1] if idx + 1 < len(md_content) else None

        if character == "$" and prev_character != "\\":
            if expect_open_delimiter:
                expect_open_delimiter = False

                if next_character == "$":
                    next_next_character = (
                        md_content[idx + 2] if idx + 2 < len(md_content) else None
                    )
                    # "$$" must be alone on a line of its own.
                    if prev_character != "\n" and prev_character is not None:
                        return MathDelimiterError.MISSING_NEWLINE_BEFORE_OPENING_DISPLAY
                    if next_next_character != "\n":
                        return MathDelimiterError.MISSING_NEWLINE_AFTER_OPENING_DISPLAY

                    expect_single_dollar = False
                    idx += 1  # Skip the second "$"; the loop increments idx again.
                else:
                    expect_single_dollar = True
            else:
                expect_open_delimiter = True

                if expect_single_dollar and next_character == "$":
                    return MathDelimiterError.DOUBLE_DOLLAR_INSTEAD_OF_CLOSING_SINGLE

                elif not expect_single_dollar:
                    if next_character != "$":
                        return (
                            MathDelimiterError.MISSING_CLOSING_DOUBLE_INSTEAD_OF_SINGLE
                        )

                    next_next_character = (
                        md_content[idx + 2] if idx + 2 < len(md_content) else None
                    )
                    if prev_character != "\n" and prev_character is not None:
                        return MathDelimiterError.MISSING_NEWLINE_BEFORE_CLOSING_DISPLAY
                    if next_next_character != "\n" and next_next_character is not None:
                        return MathDelimiterError.MISSING_NEWLINE_AFTER_CLOSING_DISPLAY

                    idx += 1  # Skip the second "$"; the loop increments idx again.

        # A newline may not appear inside an inline "$ ... $" expression.
        elif character == "\n" and not expect_open_delimiter and expect_single_dollar:
            return MathDelimiterError.INVALID_NEWLINE_INSIDE_INLINE

        idx += 1

    if expect_open_delimiter:
        return MathDelimiterError.PASSED
    elif expect_single_dollar:
        return MathDelimiterError.MISSING_CLOSING_SINGLE_DOLLAR
    else:
        return MathDelimiterError.MISSING_CLOSING_DOUBLE_DOLLAR
