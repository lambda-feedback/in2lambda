# AGENTS.md

Rules for an agent that uses in2lambda to build Lambda Feedback problem sets, or that changes in2lambda itself.

## Building a set

Write a Python script that builds a `Set` with the API in `in2lambda/api/` and calls `Set.to_json(output_dir)`. Upload the zip that `to_json` writes, unchanged. The platform imports questions in the zip's entry order, so never rezip or rename its files.

Settings left unset take their values from `in2lambda/defaults.toml`. Set only what a question needs.

### Content

- One `Question` per problem in the source, in the source's order. One `Part` per sub-question.
- Put given data in `master_content`, as a markdown table when there are more than three values.
- Put each part's final answer in `answer` and its working in `worked_solution`, with steps separated by `---`.
- Extract figures from the source and pass their paths in `Question.images`. Reference each one by file name: `![pictureTag](name.png){ width=60% }`. A figure that shows the answer belongs in the worked solution only.
- A "show that" or discussion part with no single answer gets a worked solution and no response area.

### Response areas

| Answer | Class |
|---|---|
| A number with units | `NumericUnits`, with real units: `"4 m/s"` |
| A plain number | `Number` |
| An expression | `MathSingleLine` |
| True or false | `Boolean` |
| A choice among options | `MultipleChoice`; `single=False` when more than one option is correct |

- Tolerance: `grade_params={"rtol": 0.01}` by default. Widen it only for values read from a chart or fitted from data, and say why in the worked solution.
- For an expression answer, set `"strict_syntax": False` in `grade_params`.
- For every Greek symbol in an expression, use `InputSymbol.greek(latex, code)`. It adds the unicode forms as aliases. Pass further spellings in `extra`. Never add an alias that joins a base and its subscript without `_` (`sigmaf`): the subscript may be a symbol in its own right.

### Tests

Every response area gets:

- `accept`: responses a student may give that must be marked correct. Unit conversions (`"0.4 km/s"`), rearranged expressions, unicode input (`"σ_f/ρ"`), rounding within the tolerance.
- `reject`: responses that represent typical mistakes and must be marked incorrect. A wrong exponent, a wrong unit prefix, the value from a neighbouring part, an inverted ratio.

The answer is added as a passing test automatically. `MultipleChoice` adds a failing test for each wrong option. `to_json` raises `ValueError`, naming the question and part, for an area whose tests or answer have the wrong type or shape.

in2lambda does not evaluate tests. The platform's evaluation functions do. After upload, run the teacher tests on the platform and report any that fail.

### Checking

- Recompute every numeric answer from the given data in code. Do not copy it from the source.
- Choose `accept` values well inside the tolerance and `reject` values well outside it.
- Where the source is wrong or incomplete, fix the set and list each change in the reply to the author. Examples: an answer that does not follow from the data, an equation or parameter the question needs but does not state, a true/false key that contradicts its statement.

## Changing in2lambda

- Format with `black`. Run `pytest --doctest-modules in2lambda tests` before committing.
- A rule that belongs to one response type goes in that type's class: `payload_types`, `_validate`, `_all_tests`, `_serial`, `_grade_params`. `json_convert.py` calls these on every area and names no response type.
- in2lambda checks that content is well formed: types, shapes, required fields. It never reproduces the logic of an evaluation function, such as a tolerance or an equivalence rule.
- A change to the JSON format needs evidence from a real export. Real exports are in `tests/fixtures/exports/`.
