#!/usr/bin/env python3

"""Pandoc filter for Physics Linear Algebra.

See https://pandoc.org/filters.html for more information.
"""

from typing import Optional

import panflute as pf

from tex2lambda.question import Questions
from tex2lambda.subjects._markdown import filter
from collections import deque


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

    # Question text (ListItem -> List -> Doc)
    if isinstance(elem.ancestor(3), pf.Doc):
        match type(elem):
            case pf.Para:
                pandoc_filter.solutions = deque()
                if hasattr(pandoc_filter, "question"):
                    pandoc_filter.question.append(pf.stringify(elem))
                else:
                    pandoc_filter.question = [pf.stringify(elem)]
            case pf.OrderedList:
                for listItem in elem.content:
                    part = [
                        pf.stringify(item)
                        for item in listItem.content
                        if not isinstance(item, pf.Div)
                    ]
                    questions.add_part("\n".join(part))
                    questions.add_solution_part(pandoc_filter.solutions.popleft())

    if isinstance(elem, pf.Div):
        pandoc_filter.solutions.append(pf.stringify(elem))
        if pandoc_filter.question:
            questions.add_question("\n".join(pandoc_filter.question))
            questions.add_solution_part(pf.stringify(elem))
        pandoc_filter.question = []
    return None
