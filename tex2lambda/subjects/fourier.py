#!/usr/bin/env python3

"""Pandoc filter for Fourier files (specifically by Carlo).

See https://pandoc.org/filters.html for more information.
"""

from typing import Iterator, Optional

import panflute as pf

from tex2lambda.question import Questions
from tex2lambda.subjects._markdown import filter


@filter
def pandoc_filter(
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

    # Top level ordered list (not nested parts list)
    if isinstance(elem.parent, pf.Doc) and isinstance(elem, pf.OrderedList):
        for numbered_part in elem.content:
            # For each numbered question, extract blurb and parts
            blurb: list[str] = []
            parts: Iterator[str] = iter(())
            for section in numbered_part.content:
                match type(section):
                    case pf.Para:
                        blurb.append(pf.stringify(section))
                    case pf.OrderedList:
                        parts = (pf.stringify(item) for item in section.content)

            # Use spaces hack to add newlines between blurb paragraphs
            questions.add_question("\n&#x20;&#x20;\n".join(blurb))
            for part in parts:
                questions.add_part(part)
    return None
