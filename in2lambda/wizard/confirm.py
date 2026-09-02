"""Interactive confirmation of the response areas the wizard proposes.

``in2lambda wizard`` shows the instructor each question / part alongside the
response area the LLM suggested and lets them accept it, edit it, or drop it
before the markdown is written. With ``--yes`` the suggestions are kept as-is;
with ``--no-response-areas`` they are all dropped.
"""

import json

import rich_click as click

from in2lambda.response_areas.registry import (
    EVALUATION_FUNCTIONS,
    RESPONSE_TYPES,
    functions_for,
    get,
)
from in2lambda.wizard.extract import WizardResponseArea, WizardSet


def _truncate(text: str, limit: int = 100) -> str:
    """Collapse whitespace in ``text`` and clip it to ``limit`` characters."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _prompt_params(spec) -> dict:
    """Prompt for each parameter of ``spec``; keep only the non-default answers."""
    params: dict = {}
    for param in spec.params:
        label = f"  {param.name} ({param.help})"
        if param.type == "boolean":
            value: object = click.confirm(label, default=bool(param.default))
        elif param.type == "number":
            raw = click.prompt(label, default=str(param.default))
            try:
                value = int(raw)
            except ValueError:
                try:
                    value = float(raw)
                except ValueError:
                    value = param.default
        elif param.type == "json":
            raw = click.prompt(f"{label} [JSON]", default=json.dumps(param.default))
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = param.default
        else:
            value = click.prompt(
                label, default=param.default or "", show_default=bool(param.default)
            )
        if value != param.default and value != "":
            params[param.name] = value
    return params


def _edit(existing) -> WizardResponseArea:
    """Build a response area interactively, pre-filled from ``existing`` if given."""
    click.echo()
    click.echo("  response types: " + ", ".join(RESPONSE_TYPES))
    response_type = click.prompt(
        "  response type",
        default=existing.response_type if existing else "EXPRESSION",
    )
    choices = functions_for(response_type) or list(EVALUATION_FUNCTIONS)
    click.echo("  evaluation functions: " + ", ".join(choices))
    evaluation_function = click.prompt(
        "  evaluation function",
        default=existing.evaluation_function if existing else choices[0],
    )
    answer = click.prompt("  answer", default=existing.answer if existing else "")

    spec = get(evaluation_function)
    if spec is not None:
        grade_params = _prompt_params(spec)
    else:
        grade_params = dict(existing.grade_params) if existing else {}

    return WizardResponseArea(
        response_type=response_type,
        answer=answer,
        evaluation_function=evaluation_function,
        grade_params=grade_params,
        reasoning=existing.reasoning if existing else "",
    )


def _confirm_one(label: str, target) -> None:
    """Show ``target``'s proposed response area and apply the instructor's choice.

    ``target`` is a :class:`~in2lambda.wizard.extract.WizardPart` (or, for a
    part-less question, the :class:`~in2lambda.wizard.extract.WizardQuestion`
    itself) - both expose ``text``, ``solution`` and ``response_area``.
    """
    click.echo()
    click.echo(click.style(label, bold=True))
    if target.text.strip():
        click.echo(f"  Q: {_truncate(target.text)}")
    if target.solution.strip():
        click.echo(f"  Solution: {_truncate(target.solution)}")

    proposal = target.response_area
    if proposal is None:
        if click.confirm("  No response area proposed. Add one?", default=False):
            target.response_area = _edit(None)
        return

    click.echo(
        f"  Proposed: {proposal.response_type} / {proposal.evaluation_function} "
        f"answer={proposal.answer!r} params={proposal.grade_params}"
    )
    if proposal.reasoning:
        click.echo(f"  Why: {proposal.reasoning}")

    choice = click.prompt("  [a]ccept / [e]dit / [s]kip", default="a").strip().lower()
    if choice[:1] == "s":
        target.response_area = None
    elif choice[:1] == "e":
        target.response_area = _edit(proposal)


def confirm_response_areas(
    question_set: WizardSet, *, accept_all: bool = False, enabled: bool = True
) -> WizardSet:
    """Confirm (or strip) the response area on every part of ``question_set``.

    Args:
        question_set: The extracted set; mutated in place and returned.
        accept_all: Keep every proposed response area without prompting.
        enabled: When ``False``, drop all response areas and do not prompt.

    Returns:
        The same ``question_set``.

    Examples:
        >>> from in2lambda.wizard.extract import (
        ...     WizardSet, WizardQuestion, WizardPart, WizardResponseArea)
        >>> ra = WizardResponseArea(response_type="NUMBER", answer="4",
        ...                         evaluation_function="isExactEqual")
        >>> make = lambda: WizardSet(questions=[WizardQuestion(title="t", text="",
        ...     parts=[WizardPart(text="2+2", solution="4", response_area=ra)])])
        >>> confirm_response_areas(make(), enabled=False
        ...     ).questions[0].parts[0].response_area is None
        True
        >>> confirm_response_areas(make(), accept_all=True
        ...     ).questions[0].parts[0].response_area.answer
        '4'
    """
    if not enabled:
        for question in question_set.questions:
            question.response_area = None
            for part in question.parts:
                part.response_area = None
        return question_set

    if accept_all:
        return question_set

    click.echo("Confirm the response area for each part ([a]ccept / [e]dit / [s]kip).")
    for q_index, question in enumerate(question_set.questions, start=1):
        if question.parts:
            for p_index, part in enumerate(question.parts, start=1):
                _confirm_one(f"Question {q_index}, part {p_index}", part)
        else:
            _confirm_one(f"Question {q_index}", question)
    return question_set
