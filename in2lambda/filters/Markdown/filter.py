#!/usr/bin/env python3

r"""Questions written directly in markdown, with a ``#``/``##`` structure.

The document is a flat sequence of headings and body blocks:

* A level-1 heading (``#``) starts a **new question**. Its text becomes the
  question title; the blocks that follow it (until the next heading) become the
  top-level question text.
* A level-2 heading (``##``) whose text is not ``Solution`` starts a **new part**
  of the current question. The blocks that follow become the part text.
* A level-2 heading (``##``) whose text is ``Solution`` (case-insensitive) marks
  the blocks that follow as the **worked solution** for the current part, or for
  the whole question if it has no parts yet.

When a separate answers file is supplied via ``-a``, a level-1 heading advances
to the next question and every body block is added as a worked solution
(:meth:`~in2lambda.api.question.Question.add_solution` spreads it across the
question's parts).

This is the format the ``in2lambda wizard`` command emits, and the validator in
:mod:`in2lambda.validation` checks it before conversion.
"""

from typing import Optional

import panflute as pf

from in2lambda.api.part import Part
from in2lambda.api.set import Set
from in2lambda.filters.markdown import filter

_SOLUTION_HEADING = "solution"


class _State:
    """Where the next body block should go, tracked while walking one document."""

    def __init__(self) -> None:
        self.target = "main"  # "main" | "part" | "solution"
        self.part: Optional[Part] = None


def _state_for(doc: pf.Doc) -> _State:
    """Return the parser state for ``doc``, resetting it when a new document starts.

    panflute has no per-run hook, so state is kept on the function object and
    refreshed whenever the document object identity changes (e.g. the question
    file followed by a separate answers file).
    """
    if getattr(pandoc_filter, "_doc", None) is not doc:
        pandoc_filter._doc = doc
        pandoc_filter._state = _State()
    return pandoc_filter._state


def _append(current: str, addition: str) -> str:
    """Join two blocks of text with a blank line, ignoring empty additions."""
    addition = addition.strip()
    if not addition:
        return current
    return f"{current}\n\n{addition}" if current else addition


@filter
def pandoc_filter(
    elem: pf.Element,
    doc: pf.elements.Doc,
    set: Set,
    parsing_answers: bool,
) -> Optional[pf.Str]:
    """Turn a ``#``/``##`` markdown document into questions, parts and solutions.

    Args:
        elem: The current element being processed.
        doc: The Pandoc document container.
        set: The Python API used to store the parsed result.
        parsing_answers: Whether an answers-only document is being parsed.

    Returns:
        Always ``None`` - this filter records into ``set`` rather than rewriting
        the AST (inline rewriting is handled by the shared markdown decorator).
    """
    # Only act on top-level blocks; inline elements are handled by @filter.
    if not isinstance(elem, pf.Block) or not isinstance(elem.parent, pf.Doc):
        return None

    state = _state_for(doc)
    is_heading = isinstance(elem, pf.Header)
    text = pf.stringify(elem).strip()

    if parsing_answers:
        if is_heading and elem.level == 1:
            set.increment_current_question()
        elif not is_heading and text:
            set.current_question.add_solution(text)
        return None

    if is_heading and elem.level == 1:
        set.add_question(title=text)
        state.target, state.part = "main", None
    elif is_heading and elem.level == 2 and text.lower() == _SOLUTION_HEADING:
        if state.part is None:
            state.part = Part()
            set.current_question.parts.append(state.part)
        state.target = "solution"
    elif is_heading and elem.level == 2:
        state.part = Part()
        set.current_question.parts.append(state.part)
        state.target = "part"
    elif not is_heading and text:
        if state.target == "main":
            set.current_question.main_text = text
        elif state.target == "part" and state.part is not None:
            state.part.text = _append(state.part.text, text)
        elif state.target == "solution" and state.part is not None:
            state.part.worked_solution = _append(state.part.worked_solution, text)

    return None
