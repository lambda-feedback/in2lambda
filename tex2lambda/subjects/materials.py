#!/usr/bin/env python3

"""Pandoc filter for Materials files (specifically by Jonathan Rackham).

See https://pandoc.org/filters.html for more information.
"""

from typing import Optional

import panflute as pf

from tex2lambda.question import Questions
from tex2lambda.subjects._markdown import filter


@filter
def question_filter(
    elem: pf.Element,
    doc: pf.elements.Doc,
    questions: Questions,
    tex_file: str,
) -> Optional[pf.Str]:
    """A Pandoc filter that parses and translates various TeX elements.

    Args:
        elem: The current TeX element being processed. This could be a paragraph,
            ordered list, etc.
        doc: A Pandoc document container - essentially the Pandoc AST.
        questions: The Python API that is used to store the result after processing
            the TeX file.
        tex_file: The absolute path to the TeX file being parsed.

    Returns:
        Converted TeX elements for the AST where required
        e.g. replaces math equations so that they are surrounded by $.
    """
    match type(elem):
        # Question text is stored in paragraph blocks where the preceding block is a section header.
        case pf.Para:
            if (
                isinstance(elem.prev, pf.Header)
                and pf.stringify(elem.prev) != "Solution"
            ):
                questions.add_question(pf.stringify(elem))

        # Parts are denoted via ordered lists
        case pf.OrderedList:
            for item in elem.content:
                if isinstance(item, pf.ListItem):
                    questions.add_part(pf.stringify(item))

        # Solution is in a Div with nested content being "Solution"
        case pf.Div:
            if pf.stringify(elem.content[0].content) == "Solution":
                questions.add_solution_all_parts(pf.stringify(elem)[len("Solution") :])

    return None
