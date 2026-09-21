#!/usr/bin/env python3

"""The solution appears after the question but is not explicitly broken down by part.

If a question does have parts, the same solution is added to each part on Lambda Feedback.
"""

from typing import Optional

import panflute as pf

from in2lambda.api.set import Set
from in2lambda.filters.markdown import filter


@filter
def pandoc_filter(
    elem: pf.Element,
    doc: pf.elements.Doc,
    set: Set,
    parsing_answers: bool,
) -> Optional[pf.Str]:
    """A Pandoc filter that parses and translates various TeX elements.

    Args:
        elem: The current TeX element being processed. This could be a paragraph,
            ordered list, etc.
        doc: A Pandoc document container - essentially the Pandoc AST.
        set: The Python API that is used to store the result after processing
            the TeX file.
        parsing_answers: Whether an answers-only document is currently being parsed.

    Returns:
        Converted TeX elements for the AST where required
        e.g. replaces math equations so that they are surrounded by $.
    """
    match type(elem):
        # Question text is stored in paragraph blocks where the preceding block is a section header.
        # TODO: This doesn't work if the question has more than one paragraph
        case pf.Para:
            if (
                isinstance(elem.prev, pf.Header)
                and pf.stringify(elem.prev) != "Solution"
            ):
                set.add_question(main_text=elem)

        # Parts are denoted via ordered lists
        case pf.OrderedList:
            for item in elem.content:
                set.current_question.add_part_text(item)

        # Pandoc writes a LaTeX environment it has no block for as a Div whose classes
        # hold the environment's name, so \begin{solution} becomes a Div classed
        # "solution". Some documents instead write the word Solution as the first block
        # of the Div; the filter accepts both.
        case pf.Div:
            if "solution" in elem.classes or (
                elem.content and pf.stringify(elem.content[0].content) == "Solution"
            ):
                set.current_question.add_solution(pf.stringify(elem))

    return None
