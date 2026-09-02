"""Use an LLM to pull a structured question set out of unstructured markdown.

This is the single-pass extraction used by ``in2lambda wizard``: the whole
document goes in, a :class:`WizardSet` comes back, and :func:`to_markdown`
renders it in the ``#``/``##`` form the :mod:`Markdown filter
<in2lambda.filters.Markdown.filter>` reads. Each part also carries a proposed
:class:`WizardResponseArea` (how to auto-mark it), which the instructor confirms
in :mod:`in2lambda.wizard.confirm` before it is written as a
``lambda-feedback`` block.
"""

import json
from typing import Optional

from pydantic import BaseModel, Field


class WizardResponseArea(BaseModel):
    """A proposed way to auto-mark one part, for the instructor to confirm."""

    response_type: str = Field(
        description="Input type: one of EXPRESSION, NUMBER, NUMERIC_UNITS, BOOLEAN, "
        "TEXT, ESSAY, CODE, MATRIX, TABLE, MULTIPLE_CHOICE."
    )
    answer: str = Field(description="The reference answer, as a string.")
    evaluation_function: str = Field(
        description="Evaluation function name, e.g. compareExpressions, "
        "comparePhysicalQuantities, symbolicEqual, compareBoolean, "
        "shortTextAnswer, isExactEqual."
    )
    grade_params: dict = Field(
        default_factory=dict,
        description="Parameters for the evaluation function; use {} if unsure.",
    )
    reasoning: str = Field(
        default="",
        description="One sentence explaining the chosen input type and function.",
    )


class WizardPart(BaseModel):
    """One sub-question, its worked solution, and how to mark it."""

    text: str = Field(description="The sub-question text, verbatim, without its label.")
    solution: str = Field(
        default="", description="Worked solution for this part; empty if none is given."
    )
    response_area: Optional[WizardResponseArea] = Field(
        default=None,
        description="Proposed response area derived from the solution; null when "
        "there is no solution to mark.",
    )


class WizardQuestion(BaseModel):
    """A whole question: a stem, optional parts, and solutions."""

    title: str = Field(description="A short title for the question.")
    text: str = Field(description="The question stem, before any sub-questions.")
    parts: list[WizardPart] = Field(
        default_factory=list, description="Sub-questions such as (a), (b), i., ii."
    )
    solution: str = Field(
        default="",
        description="Worked solution when the question has no parts; empty otherwise.",
    )
    response_area: Optional[WizardResponseArea] = Field(
        default=None,
        description="Proposed response area when the question has no parts; null "
        "otherwise.",
    )


class WizardSet(BaseModel):
    """Every question found in the document."""

    questions: list[WizardQuestion]


_SYSTEM_PROMPT = """\
You extract questions from problem sheets and lecture material.

Return every question with:
- a short title,
- its stem (the text before any sub-questions),
- its parts - sub-questions such as (a), (b) or i., ii. - each with the worked
  solution for that part,
- or, if the question has no parts, a single worked solution for the whole
  question.

For every part that has a worked solution, also propose a response_area - how a
student would answer it and how it should be auto-marked:
- response_type: the input widget (EXPRESSION for algebra, NUMBER for a bare
  number, NUMERIC_UNITS for a quantity with units, BOOLEAN for true/false, TEXT
  for a short phrase, ESSAY for prose, CODE for a program).
- evaluation_function: how to compare the response to the answer. Use
  compareExpressions or symbolicEqual for algebra, comparePhysicalQuantities for
  quantities with units, isExactEqual for an exact number or string,
  compareBoolean for true/false, shortTextAnswer for a short phrase, langModels
  for prose.
- answer: the reference answer as a string.
- grade_params: leave as {} unless the solution makes a specific tolerance or
  option obvious.
- reasoning: one sentence.
If a part has no solution, set response_area to null - do not invent an answer.

Copy mathematics and LaTeX exactly, keeping $...$ and $$...$$ delimiters. Do not
invent content: if a solution is not present, leave it empty. Do not include
question or part numbering in the text.\
"""

_FEWSHOT_INPUT = """\
Question 3. A ball is dropped from rest from a height $h$.
(a) Find the time it takes to reach the ground.
(b) Find its speed on impact.

Solution.
(a) $t = \\sqrt{2h/g}$.
(b) $v = \\sqrt{2gh}$.\
"""

_FEWSHOT_OUTPUT = (
    '{"questions": [{"title": "Ball dropped from height h", '
    '"text": "A ball is dropped from rest from a height $h$.", '
    '"parts": [{"text": "Find the time it takes to reach the ground.", '
    '"solution": "$t = \\\\sqrt{2h/g}$.", '
    '"response_area": {"response_type": "EXPRESSION", "answer": "sqrt(2*h/g)", '
    '"evaluation_function": "compareExpressions", "grade_params": {}, '
    '"reasoning": "The answer is a symbolic expression in h and g."}}, '
    '{"text": "Find its speed on impact.", "solution": "$v = \\\\sqrt{2gh}$.", '
    '"response_area": {"response_type": "EXPRESSION", "answer": "sqrt(2*g*h)", '
    '"evaluation_function": "compareExpressions", "grade_params": {}, '
    '"reasoning": "The answer is a symbolic expression in g and h."}}], '
    '"solution": "", "response_area": null}]}'
)


def extract_set(source_markdown: str, client, model: str) -> WizardSet:
    """Ask ``model`` (via ``client``) to turn ``source_markdown`` into a WizardSet.

    Args:
        source_markdown: The document to extract from (markdown or LaTeX text).
        client: An OpenAI-compatible client, e.g. from
            :func:`in2lambda.llm.get_client`.
        model: The model slug to use.

    Returns:
        The extracted question set.

    Raises:
        RuntimeError: if the model does not return a parseable set.
    """
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _FEWSHOT_INPUT},
            {"role": "assistant", "content": _FEWSHOT_OUTPUT},
            {"role": "user", "content": source_markdown},
        ],
        response_format=WizardSet,
    )

    parsed: Optional[WizardSet] = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("The model did not return a parseable question set.")
    return parsed


def _response_area_block(response_area: WizardResponseArea) -> str:
    """Render a response area as a ``lambda-feedback`` fenced block."""
    payload = {
        "responseType": response_area.response_type,
        "answer": response_area.answer,
        "evaluationFunction": response_area.evaluation_function,
        "gradeParams": response_area.grade_params,
    }
    return "```lambda-feedback\n" + json.dumps(payload, indent=2) + "\n```"


def to_markdown(question_set: WizardSet) -> str:
    """Render a :class:`WizardSet` as ``#``/``##`` markdown for the Markdown filter.

    Examples:
        >>> from in2lambda.wizard.extract import (
        ...     WizardSet, WizardQuestion, WizardPart, WizardResponseArea, to_markdown
        ... )
        >>> qs = WizardSet(questions=[WizardQuestion(
        ...     title="Sum", text="Add them.",
        ...     parts=[WizardPart(text="2 + 2?", solution="4",
        ...         response_area=WizardResponseArea(
        ...             response_type="NUMBER", answer="4",
        ...             evaluation_function="isExactEqual"))])])
        >>> print(to_markdown(qs))  # doctest: +NORMALIZE_WHITESPACE
        # Sum
        <BLANKLINE>
        Add them.
        <BLANKLINE>
        ## Part 1
        <BLANKLINE>
        2 + 2?
        <BLANKLINE>
        ## Solution
        <BLANKLINE>
        4
        <BLANKLINE>
        ```lambda-feedback
        {
          "responseType": "NUMBER",
          "answer": "4",
          "evaluationFunction": "isExactEqual",
          "gradeParams": {}
        }
        ```
    """
    blocks: list[str] = []

    for question in question_set.questions:
        blocks.append(f"# {question.title.strip()}")
        if question.text.strip():
            blocks.append(question.text.strip())

        if question.parts:
            for index, part in enumerate(question.parts, start=1):
                blocks.append(f"## Part {index}")
                if part.text.strip():
                    blocks.append(part.text.strip())
                if part.solution.strip():
                    blocks.append("## Solution")
                    blocks.append(part.solution.strip())
                if part.response_area is not None:
                    blocks.append(_response_area_block(part.response_area))
        else:
            if question.solution.strip():
                blocks.append("## Solution")
                blocks.append(question.solution.strip())
            if question.response_area is not None:
                blocks.append(_response_area_block(question.response_area))

    return "\n\n".join(blocks) + "\n"
