#!/usr/bin/env python3

"""Pandoc filter for Physics Linear Algebra.

See https://pandoc.org/filters.html for more information.
"""

from typing import Optional

import panflute as pf

from tex2lambda.api.module import Module
from tex2lambda.subjects._markdown import filter


@filter
def pandoc_filter(
    elem: pf.Element,
    doc: pf.elements.Doc,
    module: Module,
    parsing_answers: bool,
) -> Optional[pf.Str]:
    """A Pandoc filter that parses and translates various TeX elements.

    Args:
        elem: The current TeX element being processed. This could be a paragraph,
            ordered list, etc.
        doc: A Pandoc document container - essentially the Pandoc AST.
        module: The Python API that is used to store the result after processing
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
                if hasattr(pandoc_filter, "question"):
                    pandoc_filter.question.append(pf.stringify(elem))
                else:
                    pandoc_filter.question = [pf.stringify(elem)]
            case pf.OrderedList:
                pandoc_filter.parts = []
                for item in elem.content:
                    pandoc_filter.parts.append(pf.stringify(item))

    # Solutions are in a Div
    if isinstance(elem, pf.Div):
        module.add_question(main_text="\n".join(pandoc_filter.question))
        if hasattr(pandoc_filter, "parts"):
            for part in pandoc_filter.parts:
                module.current_question.add_part_text(part)
        pandoc_filter.question = []
        pandoc_filter.parts = []

        # If the first part of the div is an ordered list, assume part answers
        # If paragraph, extract all paragraphs as total answer
        match type(first_answer_part := elem.content[0]):
            case pf.OrderedList:
                for item in first_answer_part.content:
                    module.current_question.add_solution(pf.stringify(item))
            case pf.Para:
                module.current_question.add_solution(pf.stringify(elem))

    return None
