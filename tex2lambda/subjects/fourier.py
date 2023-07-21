#!/usr/bin/env python3

"""Pandoc filter for Fourier files (specifically by Carlo).

See https://pandoc.org/filters.html for more information.
"""

from typing import Optional

import panflute as pf

from tex2lambda.question import Questions
from tex2lambda.subjects._markdown import filter


@filter
def pandoc_filter(
    elem: pf.Element,
    doc: pf.elements.Doc,
    questions: Questions,
    parsing_answers: bool,
) -> Optional[pf.Str]:
    """A Pandoc filter that parses and translates various TeX elements.

    Args:
        elem: The current TeX element being processed. This could be a paragraph,
            ordered list, etc.
        doc: A Pandoc document container - essentially the Pandoc AST.
        questions: The Python API that is used to store the result after processing
            the TeX file.
        parsing_answers: Whether an answers-only document is currently being parsed.

    Returns:
        Converted TeX elements for the AST where required
        e.g. replaces math equations so that they are surrounded by $.
    """

    # Top level ordered list (not nested parts list)
    if isinstance(elem.parent, pf.Doc) and isinstance(elem, pf.OrderedList):
        for numbered_part in elem.content:
            if parsing_answers:
                # Denotes that we've reached the answer for a new question
                questions.increment_current_question()
            # For each numbered question, extract blurb and parts
            blurb: list[str] = []
            lettered_parts: list[str] = []
            for section in numbered_part.content:
                match type(section):
                    case pf.Para:
                        blurb.append(pf.stringify(section))
                    case pf.OrderedList:
                        lettered_parts.extend(
                            pf.stringify(item) for item in section.content
                        )

            # Use spaces hack to add newlines between blurb paragraphs
            spaced_blurb = "\n&#x20;&#x20;\n".join(blurb)

            # Answers for questions with no parts
            if parsing_answers and not lettered_parts:
                questions.add_solution_all_parts(spaced_blurb)
            # Add the main question text as the Lambda Feedback blurb
            elif not parsing_answers:
                questions.add_question(spaced_blurb)

            # Add each part solution/text
            # For the solution, prepend any top level answer text to each part answer
            for part in lettered_parts:
                questions.add_solution_part(
                    spaced_blurb + part
                ) if parsing_answers else questions.add_part(part)
    return None
