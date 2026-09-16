"""Use an LLM to pull a structured question set out of unstructured markdown.

This is the single-pass extraction used by ``in2lambda wizard``: the whole
document goes in, a :class:`WizardSet` comes back, and :func:`to_markdown`
renders it in the ``#``/``##`` form the :mod:`Markdown filter
<in2lambda.filters.Markdown.filter>` reads.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field


class WizardPart(BaseModel):
    """One sub-question and its worked solution."""

    text: str = Field(description="The sub-question text, verbatim, without its label.")
    solution: str = Field(
        default="", description="Worked solution for this part; empty if none is given."
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
        description=(
            "Overall or closing worked solution for the question, whether or not "
            "it has parts; empty if the document gives none."
        ),
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
- and an overall worked solution for the whole question, if the document gives
  one - whether that is the question's only solution (no parts) or a closing
  solution on top of the per-part ones.

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
    '"solution": "$t = \\\\sqrt{2h/g}$."}, '
    '{"text": "Find its speed on impact.", "solution": "$v = \\\\sqrt{2gh}$."}], '
    '"solution": ""}]}'
)


# ``\t``, ``\r``, ``\f`` and ``\b`` are all valid JSON string escapes, so a model
# that emits ``\text`` / ``\rho`` / ``\frac`` / ``\beta`` with a single backslash
# in its structured output has that backslash swallowed: the parsed JSON then
# holds a bare control character glued to the rest of the command (``<TAB>ext``,
# ``<FF>rac`` ...). None of those control characters is ever real text in a
# problem sheet, so a C0 control character immediately followed by a letter can
# only be a mangled LaTeX control word - put the backslash back. Newlines are
# left untouched: they carry real structure in the extracted text.
_CTRL_ESCAPES = {"\t": r"\t", "\r": r"\r", "\f": r"\f", "\b": r"\b"}
_MANGLED_COMMAND = re.compile(r"([\t\r\f\b])(?=[A-Za-z])")


def _demangle(text: str) -> str:
    r"""Restore LaTeX control words whose backslash was lost to JSON un-escaping.

    A TAB/CR/FF/BS glued to a letter (e.g. ``<TAB>ext{m}`` from ``\text``) becomes
    ``\`` + that escape letter again. Newlines are deliberately left as-is: a
    mangled ``\n``-command (``\nu``, ``\nabla``, ``\neq``, ...) is indistinguishable
    from a genuine line break once JSON has swallowed the backslash, so those
    commands are not repaired here and will surface as a broken line break rather
    than maths. This is a best-effort heuristic, not a guarantee in the other
    direction either: a genuine TAB/CR/FF/BS immediately followed by a letter
    (e.g. a tab-separated table row) is equally indistinguishable from a mangled
    command and will be incorrectly rewritten into a literal escape sequence.
    """
    return _MANGLED_COMMAND.sub(lambda match: _CTRL_ESCAPES[match.group(1)], text)


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

    for question in parsed.questions:
        question.title = _demangle(question.title)
        question.text = _demangle(question.text)
        question.solution = _demangle(question.solution)
        for part in question.parts:
            part.text = _demangle(part.text)
            part.solution = _demangle(part.solution)
    return parsed


def to_markdown(question_set: WizardSet) -> str:
    """Render a :class:`WizardSet` as ``#``/``##`` markdown for the Markdown filter."""
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

                solution = part.solution.strip()
                if index == len(question.parts) and question.solution.strip():
                    # The Markdown filter has no slot for a question-level
                    # solution once a question has parts - a "## Solution"
                    # heading after the last part is read back as that part's
                    # own solution. Fold an overall/closing solution into the
                    # last part instead of silently dropping it.
                    solution = (
                        f"{solution}\n\n{question.solution.strip()}"
                        if solution
                        else question.solution.strip()
                    )
                if solution:
                    blocks.append("## Solution")
                    blocks.append(solution)
        elif question.solution.strip():
            blocks.append("## Solution")
            blocks.append(question.solution.strip())

    return "\n\n".join(blocks) + "\n"
