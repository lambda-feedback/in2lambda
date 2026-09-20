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
...             config={
...                 "allowPhoto": True,
...                 "allowHandwrite": True,
...                 "enableRefinement": True,
...             },
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
- **Images** go in `Question.images` as paths on disk; they are copied into `media/` keeping the
  file name they already had, and referred to from the markdown by that name.
- **{meth}`Set.from_json <in2lambda.api.set.Set.from_json>`** reads an existing export, as a folder
  or a zip, so an edit to a real set can start from what Lambda Feedback produced.

## The JSON in2lambda writes

```
<set name>/set_<Name>.json
<set name>/question_000_<Title>.json          # 000 is the question's orderNumber
<set name>/question_001_...
<set name>/media/rocket-momentum.png              # one per Question.images path
<set name>.zip                                 # the folder, zipped, to upload
```

A question's filename is its title with spaces and the characters Windows and path separators
forbid (`/ \ < > : " | ?  *`) each replaced by an underscore. An image keeps the file name it
already had, so `images=["figures/rocket-momentum.png"]` gives `media/rocket-momentum.png`.
Files are written on a single line.

### Set

```{include} _autosummary/question-format/set.md
```

Each visibility is a {class}`~in2lambda.api.visibility_status.VisibilityController`, changed with
`to_open()`, `to_hide()` or `to_open_with_warnings()`.

### Question

```{include} _autosummary/question-format/question.md
```

### Part

```{include} _autosummary/question-format/part.md
```

### Response area

```{include} _autosummary/question-format/response_area.md
```

The three types in2lambda writes:

| `responseType` | `evaluationFunctionName` | `answer` | `config` and `gradeParams` |
|---|---|---|---|
| `MATH_SINGLE_LINE` | `symbolicEqual` | an expression, e.g. `(pi/6)*rho*U**2*R**2` | `gradeParams` `{"strict_syntax": false}`; `config` holds `allowPhoto`, `allowHandwrite` and `enableRefinement` |
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
written `^\circ`. An image is written `![pictureTag](rocket-momentum.png)`, naming the file as it
sits in `media/`. A filter instead passes through whatever path the source document used, so
`\includegraphics{figures/rocket-momentum.png}` becomes `![pictureTag](figures/rocket-momentum.png)`
beside `media/rocket-momentum.png`.

:::{note}
Lambda Feedback's own exports carry a few keys in2lambda neither reads nor writes, among them
`isSurvey` and `releasedAt` on the set. Diffing a written set against a real export will show
them missing; the platform fills them in on import.
:::
