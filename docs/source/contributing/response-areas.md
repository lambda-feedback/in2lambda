# Response Areas

A **response area** is where a student answers part of a question and how that
answer is auto-marked. in2lambda can carry response areas from the source
document all the way into the imported Lambda Feedback JSON.

## The model

{class}`in2lambda.api.response_area.ResponseArea` holds four things:

| Field | Meaning | Import JSON |
| --- | --- | --- |
| `response_type` | input widget - `EXPRESSION`, `NUMBER`, `NUMERIC_UNITS`, `BOOLEAN`, `TEXT`, `ESSAY`, `CODE`, ... | `response.responseInput.responseType` |
| `answer` | the reference answer, as a string | `response.responseInput.answer` |
| `evaluation_function` | which evaluation function grades the response | `evaluationFunctionName` |
| `grade_params` | that function's parameters | `gradeParams` |

`config` (extra `responseInput` settings, e.g. `{"language": "python"}` for
`CODE`) and `pre_response_text` / `post_response_text` round it out. Everything
else in the on-import entry - feedback colours, `inputSymbols`, `tests`,
`cases`, ... - comes from
`in2lambda/json_convert/minimal_template_response_area.json` and is not something
a filter sets.

A filter attaches one with
{meth}`~in2lambda.api.question.Question.add_response_area`:

```python
from in2lambda.api.response_area import ResponseArea

set.current_question.add_response_area(
    ResponseArea("EXPRESSION", "pi*d", "compareExpressions", {"rtol": 0.01})
)
```

Parts with no response area import exactly as before, with `"responseAreas": []`.

## The evaluation-function registry

{data}`in2lambda.response_areas.EVALUATION_FUNCTIONS` is in2lambda's model of the
functions documented in the [Lambda Feedback evaluation-function
reference](https://docs.lambdafeedback.com/teacher/reference/evaluation_functions/).
Each entry lists the response types it pairs with and its parameters (name,
type, default, help). It drives what `in2lambda wizard` proposes and what its
confirmation prompt offers.

`compareExpressions` and `comparePhysicalQuantities` have complete parameter
lists; the others carry their common parameters and a `TODO` pointing at the
per-function docs page. Nothing is *enforced* - `json_convert` passes an unknown
function or parameter straight through, so a newer function still imports, it
just is not offered in the menu.

## The `lambda-feedback` block

The [`Markdown` filter](../filters/_autosummary/Markdown) reads a fenced code
block whose info string is `lambda-feedback`, placed under the part or its
`## Solution`:

````markdown
## Solution

$C = \pi d$.

```lambda-feedback
{
  "responseType": "EXPRESSION",
  "answer": "pi*d",
  "evaluationFunction": "compareExpressions",
  "gradeParams": {"rtol": 0.01}
}
```
````

The body is JSON with the keys `responseType`, `answer`, `evaluationFunction`,
`gradeParams`, and optionally `config`, `preResponseText`, `postResponseText`.
`in2lambda wizard` writes these blocks after you confirm its suggestions (see
[Wizard](../wizard)); you can also hand-write or edit them. Malformed blocks are
reported by {func}`in2lambda.validation.check_markdown` as a warning - conversion
still goes ahead, the block is just ignored.
