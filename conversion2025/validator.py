from validator_classes import *


def math_delimiter_checker(md_content: str) -> ValidatorError:
    """
    Checks if the markdown content has correctly places the math delimiters.
    If there is an issue with the math delimiters, it return false.
    Otherwise it returns true.
    """
    # If true, then expect an open delimiter
    # If false, then expect a close delimiter
    expect_open_delimiter = True

    # If true, then expect a single dollar sign `$`
    # If false, then expect a double dollar sign `$$`
    expect_single_dollar = True

    idx = 0

    # Loop through the markdown content character by character
    while idx < len(md_content):

        prev_character = md_content[idx-1] if idx > 0 else None
        character = md_content[idx]
        next_character = md_content[idx+1] if idx + 1 < len(md_content) else None

        # '\$' should be treated as a single dollar sign text
        if character == '$' and prev_character != '\\':

            # Determining if the dollar should be be the start or end of a math expression
            if expect_open_delimiter:
                expect_open_delimiter = False

                # If the next character is also a dollar sign, then it is a display math expression
                if next_character == '$':
                    next_next_character = md_content[idx+2] if idx + 2 < len(md_content) else None

                    # $$ must be preceded by a newline (or be at start) and followed by a newline
                    if (prev_character != '\n' and prev_character is not None):
                        return MissingNewLineBeforeOpeningDisplayMathDelimiter
                    if next_next_character != '\n':
                        return MissingNewLineAfterOpeningDisplayMathDelimiter
                    
                    
                    # If it is a display math expression, then expect a double dollar sign
                    expect_single_dollar = False
                    idx += 1  # Skip the second $, main loop will increment idx again

                else:
                    expect_single_dollar = True
            else:
                expect_open_delimiter = True

                # If it expect a single dollar sign, then it is an inline math expression, and it should be followed by a non-dollar character
                if expect_single_dollar and next_character == '$':
                    return DoubleDollarInsteadOfClosingSingleDollar

                # If it expects a double dollar sign, and there should be newlines preceding and following it.
                elif not expect_single_dollar:
                    if next_character != '$':
                        return MissingClosingDoubleDollarInsteadOfSingleDollar
                    
                    next_next_character = md_content[idx+2] if idx + 2 < len(md_content) else None
                    if (prev_character != '\n' and prev_character is not None):
                        return MissingNewLineBeforeClosingDisplayMathDelimiter
                    
                    if next_next_character != '\n' and next_next_character is not None:
                        return MissingNewLineAfterClosingDisplayMathDelimiter
                    idx += 1  # Skip the second $, main loop will increment idx again

        # there cannot be a newline if it is between two dollar signs
        elif character == '\n' and not expect_open_delimiter and expect_single_dollar:
            return InvalidNewlineInsideInlineMathExpression
        
        idx += 1

    if expect_open_delimiter:
        return Passed
    elif expect_single_dollar:
        return MissingClosingSingleDollar
    else:
        return MissingClosingDoubleDollar