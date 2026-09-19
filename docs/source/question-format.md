# 📦 Question format

in2lambda writes the JSON that Lambda Feedback's "import from file" button reads. This page
describes that JSON, and how to build it from Python without a source document.

## Building a question in Python

A {class}`~in2lambda.api.set.Set` holds {class}`~in2lambda.api.question.Question` objects, each
holding {class}`~in2lambda.api.part.Part` objects, each holding the
{class}`~in2lambda.api.response_area.ResponseArea` boxes students type into.
{meth}`~in2lambda.api.set.Set.to_json` writes the lot.

```pycon
>>> from in2lambda.api.part import Part
>>> from in2lambda.api.question import Question
>>> from in2lambda.api.response_area import Case, InputSymbol, ResponseArea, Test
>>> from in2lambda.api.set import Set
>>> part = Part(
...     text="Find the drag, then say whether it scales.",
...     answer="$D = \\frac{\\pi}{6}\\rho U^2 R^2$",
...     worked_solution="Start from the drag coefficient.\n\n---\n\nNow substitute.",
...     response_areas=[
...         ResponseArea(
...             response_type="MATH_SINGLE_LINE",
...             answer="(pi/6)*rho*U**2*R**2",
...             evaluation_function="symbolicEqual",
...             grade_params={"strict_syntax": False},
...             pre_text="$D=$",
...             content_after="Now put in the numbers.",
...             input_symbols=[InputSymbol("\\(R\\)", "R", ["r"])],
...             tests=[Test("(pi/6)*rho*U**2*R**2", True)],
...             cases=[Case("pi*rho*U**2*R**2", "A factor is missing.", False)],
...         ),
...         ResponseArea(
...             response_type="NUMERIC_UNITS",
...             answer="30 N",
...             evaluation_function="comparePhysicalQuantities",
...             grade_params={"rtol": 0.05, "strict_syntax": False},
...             tests=[Test("30 N", True), Test("30", False)],
...         ),
...         ResponseArea(
...             response_type="MULTIPLE_CHOICE",
...             answer=[True, False],
...             config={"single": True, "options": ["Yes", "No"], "randomise": False},
...             evaluation_function="arrayEqual",
...         ),
...     ],
... )
>>> question = Question(
...     title="Drag on a sphere",
...     main_text="A sphere of radius $R$ moves at $U$ through a fluid of density $\\rho$.",
...     parts=[part],
...     skill=1 / 3,
...     guidance="Practice at forming a drag force from a coefficient.",
...     duration_lower_bound=5,
...     duration_upper_bound=10,
... )
>>> question_set = Set(questions=[question])
>>> question_set.set_name("Fluids")
>>> question_set.set_description("Week 1")

```

{meth}`~in2lambda.api.set.Set.to_json` writes a folder named after the set, and a zip of it to
upload:

```pycon
>>> import json, os, tempfile
>>> with tempfile.TemporaryDirectory() as out_dir:
...     question_set.to_json(out_dir)
...     sorted(os.listdir(out_dir))
...     sorted(os.listdir(f"{out_dir}/Fluids"))
...     with open(f"{out_dir}/Fluids/question_000_Drag_on_a_sphere.json") as file:
...         written = json.load(file)
['Fluids', 'Fluids.zip']
['question_000_Drag_on_a_sphere.json', 'set_Fluids.json']
>>> [
...     area["response"]["responseInput"]["responseType"]
...     for area in written["parts"][0]["responseAreas"]
... ]
['MATH_SINGLE_LINE', 'NUMERIC_UNITS', 'MULTIPLE_CHOICE']

```

A few things the example shows in passing:

- **Building parts directly beats the incremental helpers.** [Filters](filters/index)
  read a document in order, so they call
  {meth}`~in2lambda.api.question.Question.add_part_text` and
  {meth}`~in2lambda.api.question.Question.add_solution`, which fill in whichever part comes next.
  A script that already knows the whole question should pass `Part` objects to `Question`, as
  above; only those give a part a final answer or an answer box.
- **A line holding only `---` (or `***`) splits a worked solution** into the steps students go
  through one at a time in the structured tutorial.
- **Unset question settings are left out of the JSON** rather than guessed at, so `skill`,
  `guidance` and the two durations only appear when set. `publish` and the four `display_*`
  settings always do, defaulting to `True`.
- **Images** go in `Question.images` as paths on disk; they are copied into `media/` and referred
  to from the markdown by basename.
- **{meth}`Set.from_json <in2lambda.api.set.Set.from_json>`** reads an existing export, as a folder
  or a zip, so an edit to a real set can start from what Lambda Feedback produced.

## The JSON in2lambda writes

```
<set name>/set_<Name>.json
<set name>/question_000_<Title>.json          # 000 is the question's orderNumber
<set name>/question_001_...
<set name>/media/question_000_<Title>_0001.png
<set name>.zip                                 # the folder, zipped, to upload
```

A question's filename is its title with spaces and the characters Windows and path separators
forbid (`/ \ < > : " | ?  *`) each replaced by an underscore. Files are written on a single line.

### Set

| key | set by | meaning |
|---|---|---|
| `name` | `Set.set_name` | names the folder, the zip and the file |
| `description` | `Set.set_description` | shown with the set |
| `finalAnswerVisibility` | `Set._finalAnswerVisibility` | `OPEN`, `HIDE` or `OPEN_WITH_WARNINGS` |
| `workedSolutionVisibility` | `Set._workedSolutionVisibility` | as above |
| `structuredTutorialVisibility` | `Set._structuredTutorialVisibility` | as above |
| `manuallyHidden` | fixed by template (`true`) | |
| `chatbotVisibility` | fixed by template (`"HIDE"`) | |

Each visibility is a {class}`~in2lambda.api.visibility_status.VisibilityController`, changed with
`to_open()`, `to_hide()` or `to_open_with_warnings()`.

### Question

| key | set by | meaning |
|---|---|---|
| `orderNumber` | position in `Set.questions`, from 0 | matches the filename |
| `title` | `Question.title` | shown to students; an empty title becomes `Question N` |
| `masterContent` | `Question.main_text` | markdown shared by every part: setup, data, figure |
| `skill` | `Question.skill` | difficulty; exports use 1/3 and 2/3. Omitted if unset |
| `guidance` | `Question.guidance` | a sentence to students about the question's purpose. Omitted if unset |
| `durationLowerBound`, `durationUpperBound` | `Question.duration_lower_bound`, `.duration_upper_bound` | expected minutes. Omitted if unset |
| `publish` | `Question.publish` | |
| `displayFinalAnswer` | `Question.display_final_answer` | |
| `displayWorkedSolution` | `Question.display_worked_solution` | |
| `displayStructuredTutorial` | `Question.display_structured_tutorial` | |
| `displayChatbot` | `Question.display_chatbot` | |
| `parts` | `Question.parts` | ordered from 0; students see (a), (b), ... |

### Part

| key | set by | meaning |
|---|---|---|
| `orderNumber` | position in `Question.parts`, from 0 | |
| `content` | `Part.text` | markdown for this part |
| `answerContent` | `Part.answer` | the final answer shown to students, markdown |
| `responseAreas` | `Part.response_areas` | the answer boxes; may be empty |
| `workedSolution.content` | `Part.worked_solution` | markdown, split into tutorial steps on `---` |
| `workedSolution.children` | fixed by template (`[]`) | |

### Response area

| key | set by | meaning |
|---|---|---|
| `orderNumber` | position in `Part.response_areas`, from 0 | |
| `preResponseText`, `postResponseText` | `pre_text`, `post_text` | labels either side of the box |
| `contentAfter` | `content_after` | markdown shown after the box, before the next one |
| `inputSymbols` | `input_symbols` | see below |
| `displayInputSymbols` | `display_input_symbols` | whether students are shown the palette |
| `evaluationFunctionName` | `evaluation_function` | how Lambda Feedback marks the response |
| `gradeParams` | `grade_params` | that function's settings; see below |
| `livePreview` | `live_preview` | render what is typed as the student types |
| `includeInPdf` | `include_in_pdf` | |
| `saveAllowed` | `save_allowed` | |
| `separateFeedback` | `separate_feedback` | |
| `commonFeedbackColor`, `correctFeedbackColor`, `correctFeedbackPrefix`, `incorrectFeedbackColor`, `incorrectFeedbackPrefix` | `common_feedback_color`, `correct_feedback_color`, `correct_feedback_prefix`, `incorrect_feedback_color`, `incorrect_feedback_prefix` | default to what Lambda Feedback fills in |
| `tests` | `tests` | see below |
| `cases` | `cases` | see below |
| `response.responseInput.responseType` | `response_type` | which box students get |
| `response.responseInput.answer` | `answer` | the correct answer |
| `response.responseInput.config` | `config` | the box's own settings; see below |

The three types in2lambda writes:

| `responseType` | `evaluationFunctionName` | `answer` | `config` and `gradeParams` |
|---|---|---|---|
| `MATH_SINGLE_LINE` | `symbolicEqual` | an expression, e.g. `(pi/6)*rho*U**2*R**2` | `gradeParams` `{"strict_syntax": false}`; `config` holds `allowPhoto`, `allowHandwrite` and `enableRefinement`, or is null |
| `NUMERIC_UNITS` | `comparePhysicalQuantities` | a number and a unit, e.g. `0.106 kg` | `gradeParams` holds `rtol` (and `strict_syntax`); `config` is null |
| `MULTIPLE_CHOICE` | `arrayEqual` | a list of booleans, one per option | `config` holds `single`, `options` and `randomise`; `gradeParams` is null |

The three lists an area carries, each a dataclass in
{mod}`in2lambda.api.response_area`:

- `inputSymbols` — `{"symbol", "code", "aliases", "isVisible"}` from
  {class}`~in2lambda.api.response_area.InputSymbol`. `symbol` is what students see
  (e.g. `\(\rho\)`), `code` what the evaluation function reads.
- `tests` — `{"id", "payload", "expectedResponse": {"isCorrect"}}` from
  {class}`~in2lambda.api.response_area.Test`: the author's own checks of the marking.
- `cases` — `{"id", "answer", "feedback", "isCorrect", "params"}` from
  {class}`~in2lambda.api.response_area.Case`: a response matching `answer` is shown `feedback`,
  and may be marked correct.

An `id` left unset is a fresh UUID, which is what import needs.

### Markdown

Maths is `$...$` inline and `$$` on its own lines for display, rendered by
[KaTeX](https://katex.org/): commands KaTeX lacks do not display — degrees, for example, are
written `^\circ`. Images are written `![pictureTag](question_000_Title_0001.png){ width=60% }`,
naming the file in `media/`.

:::{note}
Lambda Feedback's own exports carry a few keys in2lambda neither reads nor writes, among them
`isSurvey` and `releasedAt` on the set. Diffing a written set against a real export will show
them missing; the platform fills them in on import.
:::
