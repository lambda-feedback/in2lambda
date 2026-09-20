"""Builds the key tables on the question format page from the real exports.

Those tables used to be written by hand, so a change to Lambda Feedback's schema left
the page quietly describing the old one. They are now collected at docs build from the
exports in ``tests/fixtures/exports``: one table per kind of object, listing every key
those exports carry, its JSON type and an example value. What a key *means* cannot come
from the data, so it is kept in ``NOTES`` below, and a key with no note is an error
rather than a blank cell.
"""

import json
from pathlib import Path
from typing import Any, Iterator, Sequence

EXPORTS_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "exports"
"""Real Lambda Feedback exports, the same ones the test suite round-trips."""

EXPORTS = sorted(path for path in EXPORTS_DIR.iterdir() if path.is_dir())
"""Every export folder, found rather than listed, as the test suite finds them."""

OUT_DIR = Path(__file__).parent / "_autosummary" / "question-format"
"""Where the tables are written for ``question-format.md`` to include."""

NOTES: dict[str, dict[str, str]] = {
    "set": {
        "name": "`Set.set_name` — names the folder, the zip and the file",
        "description": "`Set.set_description` — shown with the set",
        "isSurvey": "Neither read nor written by in2lambda; import fills it in",
        "releasedAt": "Neither read nor written by in2lambda; import fills it in",
        "manuallyHidden": "Fixed by the template (`true`)",
        "finalAnswerVisibility": (
            "`Set._finalAnswerVisibility` — `OPEN`, `HIDE` or `OPEN_WITH_WARNINGS`"
        ),
        "workedSolutionVisibility": "`Set._workedSolutionVisibility` — as above",
        "structuredTutorialVisibility": "`Set._structuredTutorialVisibility` — as above",
        "chatbotVisibility": 'Fixed by the template (`"HIDE"`), whatever an export says',
    },
    "question": {
        "orderNumber": "Position in `Set.questions`, from 0; matches the filename",
        "title": "`Question.title` — shown to students; an empty title becomes `Question N`",
        "masterContent": (
            "`Question.main_text` — markdown shared by every part: setup, data, figure"
        ),
        "skill": "`Question.skill` — difficulty; exports use 1/3 and 2/3. Omitted if unset",
        "guidance": (
            "`Question.guidance` — a sentence to students about the question's purpose."
            " Omitted if unset"
        ),
        "durationLowerBound": (
            "`Question.duration_lower_bound` — expected minutes. Omitted if unset"
        ),
        "durationUpperBound": (
            "`Question.duration_upper_bound` — expected minutes. Omitted if unset"
        ),
        "publish": "`Question.publish` — whether the question is visible to students",
        "displayFinalAnswer": "`Question.display_final_answer`",
        "displayWorkedSolution": "`Question.display_worked_solution`",
        "displayStructuredTutorial": "`Question.display_structured_tutorial`",
        "displayChatbot": "`Question.display_chatbot`",
        "parts": "`Question.parts` — ordered from 0; students see (a), (b), ...",
    },
    "part": {
        "orderNumber": "Position in `Question.parts`, from 0",
        "content": "`Part.text` — markdown for this part",
        "answerContent": "`Part.answer` — the final answer shown to students, markdown",
        "responseAreas": "`Part.response_areas` — the answer boxes; may be empty",
        "workedSolution.content": (
            "`Part.worked_solution` — markdown, split into tutorial steps on `---`"
        ),
        "workedSolution.children": "Fixed by the template (`[]`)",
    },
    "response_area": {
        "orderNumber": "Position in `Part.response_areas`, from 0",
        "preResponseText": "`pre_text` — the label before the box",
        "postResponseText": "`post_text` — the label after the box",
        "contentAfter": "`content_after` — markdown shown after the box, before the next",
        "inputSymbols": "`input_symbols` — the symbol palette; see below",
        "displayInputSymbols": (
            "`display_input_symbols` — whether students are shown the palette"
        ),
        "evaluationFunctionName": (
            "`evaluation_function` — how Lambda Feedback marks the response"
        ),
        "gradeParams": "`grade_params` — that function's settings; see below",
        "livePreview": "`live_preview` — render what is typed as the student types",
        "includeInPdf": "`include_in_pdf` — whether the box appears in the printed question",
        "saveAllowed": "`save_allowed` — whether a response can be saved unsubmitted",
        "separateFeedback": "`separate_feedback` — show feedback apart from the mark",
        "commonFeedbackColor": (
            "`common_feedback_color` — defaults to what Lambda Feedback fills in"
        ),
        "correctFeedbackColor": (
            "`correct_feedback_color` — defaults to what Lambda Feedback fills in"
        ),
        "correctFeedbackPrefix": (
            "`correct_feedback_prefix` — defaults to what Lambda Feedback fills in"
        ),
        "incorrectFeedbackColor": (
            "`incorrect_feedback_color` — defaults to what Lambda Feedback fills in"
        ),
        "incorrectFeedbackPrefix": (
            "`incorrect_feedback_prefix` — defaults to what Lambda Feedback fills in"
        ),
        "tests": "`tests` — the author's own checks of the marking; see below",
        "cases": "`cases` — feedback for particular responses; see below",
        "response.responseInput.responseType": "`response_type` — which box students get",
        "response.responseInput.answer": "`answer` — the correct answer",
        "response.responseInput.config": "`config` — the box's own settings; see below",
    },
}
"""What each key means, per kind of object, keyed by the key path in the table."""


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def _flatten(
    obj: dict, notes: dict[str, str], path: str = ""
) -> Iterator[tuple[str, Any]]:
    """Each key path in `obj` and its value.

    A key holding an object is descended into, so that `workedSolution` becomes
    `workedSolution.content`, unless it has a note of its own — `gradeParams` and
    `config` hold whatever the box type needs, and are described in prose instead.
    An empty object is a row like any other: descending into it would yield nothing,
    so a new key holding `{}` would go unnoticed rather than asking for a note.
    """
    for key, value in obj.items():
        full_path = f"{path}{key}"
        if isinstance(value, dict) and value and full_path not in notes:
            yield from _flatten(value, notes, f"{full_path}.")
        else:
            yield full_path, value


def _keys(objects: list[dict], notes: dict[str, str]) -> dict[str, dict]:
    """Every key path the objects carry, in order of first appearance."""
    keys: dict[str, dict] = {}
    for obj in objects:
        for path, value in _flatten(obj, notes):
            key = keys.setdefault(path, {"types": set(), "example": value, "seen": 0})
            key["seen"] += 1
            key["types"].add(_json_type(value))
            # An empty string or list says nothing about the key, so keep looking.
            if key["example"] in (None, "", [], {}):
                key["example"] = value
    for key in keys.values():
        key["optional"] = key["seen"] < len(objects)
    return keys


def _cell(value: Any) -> str:
    """One example value, short enough to sit in a table and not read as markdown."""
    example = json.dumps(value)
    if len(example) > 40:
        example = f"{example[:39]}…"
    return f"`{example.replace('|', chr(92) + '|')}`"


def _table(keys: dict[str, dict], notes: dict[str, str]) -> str:
    rows = ["| key | type | example | meaning |", "|---|---|---|---|"]
    for path, key in keys.items():
        types = " or ".join(sorted(key["types"]))
        if key["optional"]:
            types += ", optional"
        rows.append(f"| `{path}` | {types} | {_cell(key['example'])} | {notes[path]} |")
    return "\n".join(rows) + "\n"


def _roots(export_dirs: Sequence[Path]) -> dict[str, list[dict]]:
    """The objects each table is rooted on, gathered from every export."""
    roots: dict[str, list[dict]] = {
        "set": [],
        "question": [],
        "part": [],
        "response_area": [],
    }
    for export_dir in export_dirs:
        for file in sorted(export_dir.glob("set_*.json")):
            roots["set"].append(json.loads(file.read_text()))
        for file in sorted(export_dir.glob("question_*.json")):
            question = json.loads(file.read_text())
            roots["question"].append(question)
            for part in question.get("parts", []):
                roots["part"].append(part)
                roots["response_area"] += part.get("responseAreas", [])
    return roots


def generate_question_format_tables(
    export_dirs: Sequence[Path] = EXPORTS, out_dir: Path = OUT_DIR
) -> None:
    """Write a markdown table of keys per kind of object for the page to include.

    Args:
        export_dirs: Lambda Feedback export folders to read the keys from.
        out_dir: where `set.md`, `question.md`, `part.md` and `response_area.md` go.

    Raises:
        ValueError: if an export carries a key with no note in `NOTES`, or a note
            names a key no export carries. Either way the page and the schema have
            drifted apart, and the error names every key that has to be dealt with.
    """
    collected = {
        kind: _keys(objects, NOTES[kind])
        for kind, objects in _roots(export_dirs).items()
    }

    drifted = []
    for kind, keys in collected.items():
        notes = NOTES[kind]
        drifted += [f"{kind}: no note for {path}" for path in keys if path not in notes]
        drifted += [
            f"{kind}: note for {path}, which no export carries"
            for path in notes
            if path not in keys
        ]
    if drifted:
        raise ValueError("; ".join(drifted))

    out_dir.mkdir(parents=True, exist_ok=True)
    for kind, keys in collected.items():
        (out_dir / f"{kind}.md").write_text(_table(keys, NOTES[kind]))
