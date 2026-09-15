# Real Lambda Feedback exports

Each folder here is a question set exactly as Lambda Feedback exported it. Do not edit, reformat
or re-save these files: their value is that they are what the platform really produces. To add
coverage, add another export as a new folder.

## What an export contains

```
set_<Name>.json
question_000_<Title_with_underscores>.json     # 000 is the question's orderNumber
question_001_...
media/question_000_<Title>_0001.png            # referenced from the questions by basename
```

JSON files are written on a single line.

## Set

`name`, `description`, `isSurvey`, `releasedAt`, `manuallyHidden`, and the visibility of final
answers, worked solutions, structured tutorials and the chatbot.

## Question

| key | meaning |
|---|---|
| `orderNumber` | position in the set, from 0; matches the filename |
| `title` | shown to students |
| `skill` | difficulty (exports use 1/3 and 2/3) |
| `guidance` | a sentence to students about the question's purpose |
| `durationLowerBound`, `durationUpperBound` | expected minutes |
| `masterContent` | markdown shared by every part: setup, data, figure |
| `publish`, `displayFinalAnswer`, `displayStructuredTutorial`, `displayWorkedSolution`, `displayChatbot` | booleans |
| `parts` | ordered from 0; students see (a), (b), ... |

## Part

| key | meaning |
|---|---|
| `content` | markdown for this part |
| `answerContent` | the final answer shown to students, markdown |
| `responseAreas` | the answer boxes; may be empty |
| `workedSolution` | `{"content": ..., "children": []}`; optional. A line containing only `---` (or `***`) splits the content into the steps of the structured tutorial |

## Response area

Every area carries the same keys: `orderNumber`, `preResponseText` and `postResponseText` (labels
either side of the box), `contentAfter` (markdown shown after the box, before the next one),
`inputSymbols`, `displayInputSymbols`, `evaluationFunctionName`, `gradeParams`, `livePreview`,
`includeInPdf`, `saveAllowed`, the feedback settings (`separateFeedback` and the colour and
prefix fields), `tests`, `cases` and `response`.

`response.responseInput` holds `responseType`, the correct `answer`, and a `config`. The pairings
in these exports:

| responseType | evaluationFunctionName | answer | notes |
|---|---|---|---|
| `MATH_SINGLE_LINE` | `symbolicEqual` | expression, e.g. `(pi/6)*rho*U**2*R**2` | `gradeParams` `{"strict_syntax": false}` |
| `NUMERIC_UNITS` | `comparePhysicalQuantities` | number and unit, e.g. `0.106 kg` | `gradeParams` includes `rtol`; `config` is null |
| `MULTIPLE_CHOICE` | `arrayEqual` | list of booleans, one per option | `config` has `single`, `options`, `randomise`; `gradeParams` null |

- `inputSymbols`: `{"symbol": "\\(\\rho\\)", "code": "rho", "aliases": [...], "isVisible": true}`. `symbol` is what students see, `code` what the evaluator reads.
- `tests`: `{"id", "payload", "expectedResponse": {"isCorrect"}}`, the author's checks of the marking.
- `cases`: `{"id", "answer", "feedback", "isCorrect", "params"}`. A response matching `answer` is shown `feedback`, and may be marked correct.

## Markdown

Maths uses `$...$` inline and `$$` on its own lines for display, rendered by KaTeX: commands
KaTeX lacks do not display (degrees written `^\circ`, for example). Images are written
`![pictureTag](question_000_Title_0001.png){ width=60% }`.
