#!/usr/bin/env python3

"""A solution appears after each individual part."""

from collections import deque
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
                    set.current_question.add_part_text("\n".join(part))
                    set.current_question.add_solution(
                        pandoc_filter.solutions.popleft()
                    )

    if isinstance(elem, pf.Div):
        pandoc_filter.solutions.append(pf.stringify(elem))
        if pandoc_filter.question:
            set.add_question(main_text="\n".join(pandoc_filter.question))
            set.current_question.add_solution(pf.stringify(elem))
            set.current_question._last_part["solution"] -= 1
        pandoc_filter.question = []
    return None
