"""How the document beside this file writes a question and a solution: in its markup.

A `text~` constraint cannot tell these apart, because the paragraph about marks begins
with the word Question as surely as the questions themselves do. What tells them apart
is the bold and the italics, which is markup rather than text, so it takes a predicate.
"""

import panflute as pf


def bold_lead(element: pf.Element) -> bool:
    """Whether a block begins in bold, which is how a question is written here."""
    return isinstance(_lead(element), pf.Strong)


def italic_lead(element: pf.Element) -> bool:
    """Whether a block begins in italics, which is how a solution is written here."""
    return isinstance(_lead(element), pf.Emph)


def _lead(element: pf.Element) -> pf.Element:
    """What a block starts with, past the spans the source is parsed wrapped in.

    A frozen source is parsed with sourcepos, so that a block knows which lines it came
    from, and that leaves every inline inside a span carrying where it is. A predicate
    looking at the markup has to see through them.
    """
    first = element.content[0] if element.content else None
    while isinstance(first, pf.Span) and first.content:
        first = first.content[0]
    return first
