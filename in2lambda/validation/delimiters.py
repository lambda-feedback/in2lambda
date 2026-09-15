"""Checks that ``$ ... $`` and ``$$ ... $$`` math delimiters are balanced and placed correctly.

KaTeX (and Lambda Feedback) expect inline math wrapped in single dollar signs on
one line, and display math wrapped in ``$$`` that each sit alone on their own
line. This module scans markdown character by character and reports the first
delimiter mistake it finds.
"""

from dataclasses import dataclass
from enum import Enum


class MathDelimiterError(Enum):
    """A specific delimiter mistake found by :func:`math_delimiter_checker`.

    The value is a short human-readable message suitable for showing on the
    command line.
    """

    MISSING_NEWLINE_BEFORE_OPENING_DISPLAY = "opening $$ must start its own line"
    MISSING_NEWLINE_AFTER_OPENING_DISPLAY = "opening $$ must be followed by a newline"
    DOUBLE_DOLLAR_INSTEAD_OF_CLOSING_SINGLE = "inline $ ... $ closed with $$"
    MISSING_CLOSING_DOUBLE_INSTEAD_OF_SINGLE = (
        "display $$ ... $$ closed with a single $"
    )
    MISSING_NEWLINE_BEFORE_CLOSING_DISPLAY = "closing $$ must start its own line"
    MISSING_NEWLINE_AFTER_CLOSING_DISPLAY = "closing $$ must be followed by a newline"
    MISSING_CLOSING_SINGLE_DOLLAR = "unclosed inline $ ... $"
    MISSING_CLOSING_DOUBLE_DOLLAR = "unclosed display $$ ... $$"


@dataclass(frozen=True)
class MathDelimiterProblem:
    """A single delimiter mistake and the (1-based) line it was found on."""

    line: int
    error: MathDelimiterError

    def __str__(self) -> str:
        return f"line {self.line}: {self.error.value}"


def math_delimiter_checker(md_content: str) -> list[MathDelimiterProblem]:
    r"""Scan markdown for every math-delimiter mistake.

    ``\$`` is treated as a literal dollar sign, not a delimiter.

    Args:
        md_content: The markdown text to check.

    Returns:
        A list of :class:`MathDelimiterProblem`, one per mistake found, in
        the order they occur. An empty list means the delimiters are well
        formed.

    Examples:
        >>> from in2lambda.validation.delimiters import math_delimiter_checker
        >>> math_delimiter_checker("An inline $x = y$ expression.")
        []
        >>> math_delimiter_checker("Display:\n$$\nx = y\n$$")
        []
        >>> math_delimiter_checker("This costs \\$5, no math here.")
        []
        >>> math_delimiter_checker("Run `echo $PATH` now.")
        []
        >>> math_delimiter_checker("Broken $x = y")
        [MathDelimiterProblem(line=1, error=<MathDelimiterError.MISSING_CLOSING_SINGLE_DOLLAR: 'unclosed inline $ ... $'>)]
    """
    problems: list[MathDelimiterProblem] = []

    def report(error: MathDelimiterError) -> None:
        problems.append(MathDelimiterProblem(md_content.count("\n", 0, idx) + 1, error))

    # False once we are inside a math expression and awaiting its closing delimiter.
    expect_open_delimiter = True
    # While inside an expression, whether it opened with a single "$" (inline) or "$$" (display).
    expect_single_dollar = True
    # Line on which the currently open (unclosed) expression started.
    open_line = 1

    # Backtick code spans/fences are not markdown math and must not be scanned for
    # "$" delimiters, e.g. a shell variable like `echo $PATH` or a fenced snippet.
    in_fence = False
    fence_marker_len = 0
    in_code_span = False
    code_span_marker_len = 0

    idx = 0
    while idx < len(md_content):
        prev_character = md_content[idx - 1] if idx > 0 else None
        character = md_content[idx]
        next_character = md_content[idx + 1] if idx + 1 < len(md_content) else None

        if character == "`" and prev_character != "`":
            run_len = 0
            while idx + run_len < len(md_content) and md_content[idx + run_len] == "`":
                run_len += 1
            line_start = md_content.rfind("\n", 0, idx) + 1
            at_line_start = md_content[line_start:idx].strip() == ""

            if in_fence:
                line_end = md_content.find("\n", idx + run_len)
                if line_end == -1:
                    line_end = len(md_content)
                if (
                    run_len >= fence_marker_len
                    and at_line_start
                    and md_content[idx + run_len : line_end].strip() == ""
                ):
                    in_fence, fence_marker_len = False, 0
            elif in_code_span:
                if run_len == code_span_marker_len:
                    in_code_span, code_span_marker_len = False, 0
            elif run_len >= 3 and at_line_start:
                in_fence, fence_marker_len = True, run_len
            else:
                in_code_span, code_span_marker_len = True, run_len

            idx += 1
            continue

        if in_fence or in_code_span:
            idx += 1
            continue

        if character == "$" and prev_character != "\\":
            if expect_open_delimiter:
                expect_open_delimiter = False
                open_line = md_content.count("\n", 0, idx) + 1

                if next_character == "$":
                    next_next_character = (
                        md_content[idx + 2] if idx + 2 < len(md_content) else None
                    )
                    # "$$" must sit alone on its own line.
                    if prev_character != "\n" and prev_character is not None:
                        report(
                            MathDelimiterError.MISSING_NEWLINE_BEFORE_OPENING_DISPLAY
                        )
                        expect_open_delimiter, expect_single_dollar = True, True
                    elif next_next_character != "\n":
                        report(MathDelimiterError.MISSING_NEWLINE_AFTER_OPENING_DISPLAY)
                        expect_open_delimiter, expect_single_dollar = True, True
                    else:
                        expect_single_dollar = False
                    idx += 1  # Skip the second "$"; the loop increments idx again.
                else:
                    expect_single_dollar = True
            else:
                expect_open_delimiter = True

                if expect_single_dollar and next_character == "$":
                    report(MathDelimiterError.DOUBLE_DOLLAR_INSTEAD_OF_CLOSING_SINGLE)
                    expect_open_delimiter, expect_single_dollar = True, True

                elif not expect_single_dollar:
                    if next_character != "$":
                        report(
                            MathDelimiterError.MISSING_CLOSING_DOUBLE_INSTEAD_OF_SINGLE
                        )
                        expect_open_delimiter, expect_single_dollar = True, True
                    else:
                        next_next_character = (
                            md_content[idx + 2] if idx + 2 < len(md_content) else None
                        )
                        if prev_character != "\n" and prev_character is not None:
                            report(
                                MathDelimiterError.MISSING_NEWLINE_BEFORE_CLOSING_DISPLAY
                            )
                            expect_open_delimiter, expect_single_dollar = True, True
                        elif (
                            next_next_character != "\n"
                            and next_next_character is not None
                        ):
                            report(
                                MathDelimiterError.MISSING_NEWLINE_AFTER_CLOSING_DISPLAY
                            )
                            expect_open_delimiter, expect_single_dollar = True, True

                        idx += 1  # Skip the second "$"; the loop increments idx again.

        idx += 1

    if not expect_open_delimiter:
        problems.append(
            MathDelimiterProblem(
                open_line,
                (
                    MathDelimiterError.MISSING_CLOSING_SINGLE_DOLLAR
                    if expect_single_dollar
                    else MathDelimiterError.MISSING_CLOSING_DOUBLE_DOLLAR
                ),
            )
        )

    return problems
