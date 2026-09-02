# Writing a Filter

A **filter** teaches in2lambda how to read one particular document structure. If
your source doesn't parse cleanly with any of the built-in filters, this page
walks through deciding whether you actually need a new one and, if so, writing it.

## 1. Do you need a filter?

You have two ways to get an unusual document into Lambda Feedback.

| | `in2lambda wizard` | A new filter |
| --- | --- | --- |
| **How** | OCR + an LLM turn the document into `#`/`##` markdown you review, then `in2lambda convert draft.md Markdown` | A small Python parser matched to the document's structure |
| **Best when** | The layout is messy, inconsistent, OCR'd, or a one-off; you're happy to eyeball the result | The layout is regular and recurring (a course's standard problem sheets, a publisher template) |
| **Cost** | Needs `in2lambda[llm]`, an `OPENROUTER_API_KEY`, and (for PDFs) Mathpix keys; per-run API cost | None - deterministic and offline |
| **Fidelity** | Whatever the model extracts | Exactly what you program, including per-part solutions, separate answer files, and `\graphicspath` figures |

Before writing anything, check whether an existing filter already fits - the CLI
name is case-insensitive:

| Filter | Structure it expects |
| --- | --- |
| `PartsSepSol` | Questions in a top-level `enumerate`; a nested `enumerate` gives the parts. Any answers are in a **separate file** with the same shape. |
| `PartsOneSol` | Question text, then parts as an ordered list, then **one** `Solution` applied to every part. |
| `PartPartSolSol` | All part texts first, then all part solutions together in a `Solution` block. |
| `PartSolPartSol` | Each part is immediately followed by its own solution. |
| `Markdown` | Flat `#` question / `##` part / `## Solution` markdown - the format the wizard emits. |

If none of those match and the structure is worth automating, carry on.

## 2. How a filter fits in

```
document ──pandoc──▶ AST ──panflute filter──▶ Set object ──json_convert──▶ Lambda Feedback zip
```

pandoc turns the source into a standard AST; your filter walks that AST and
records what it finds into a {class}`~in2lambda.api.set.Set`; `json_convert` then
writes the importable JSON/zip. See [High Level Overview](high_level) for the
bigger picture.

Every filter's `pandoc_filter` is wrapped by the `@filter` decorator in
`in2lambda/filters/markdown.py`, which has **already** handled the inline details
by the time your function runs:

- maths is wrapped in `$…$` / `$$…$$`,
- images become `![pictureTag](url)` and their paths are collected into
  `set.current_question.images`,
- bold and italic are converted to markdown.

So your `pandoc_filter` only has to route **block-level** elements (paragraphs,
lists, `Div`s, headers) into the `Set` API.

## 3. Scaffold it

```shell
$ python scripts/new_filter.py MyFilter        # LaTeX example
$ python scripts/new_filter.py MyFilter --md   # markdown example
```

This creates `in2lambda/filters/MyFilter/` with `__init__.py`, a `filter.py`
skeleton, and an `example.tex` (or `example.md`). The CLI discovers filters by
listing that directory, so `in2lambda convert` picks the new one up immediately -
there is nothing to register.

## 4. Write the example first

Trim `example.tex` / `example.md` down to the **smallest** self-contained
document that still shows every structural feature your filter handles: question
stems, at least two parts, at least one worked solution, and - if relevant - a
matching separate answers file or a figure.

This file does double duty: it's the example embedded in the filter's
auto-generated documentation page, and it's the fixture the end-to-end tests run
your filter against.

## 5. Implement `pandoc_filter`

Open the built-in filter whose structure is closest to yours and copy its
approach. The signature is always:

```python
@filter
def pandoc_filter(
    elem: pf.Element,
    doc: pf.elements.Doc,
    set: Set,
    parsing_answers: bool,
) -> Optional[pf.Str]:
```

panflute calls it once per element as it walks the tree. Return `None` to leave
the tree alone (recording into `set` is a side effect); the decorator handles the
rewrites you don't need to think about.

### Inspecting the AST

- `match type(elem):` against `pf.Para`, `pf.OrderedList`, `pf.DefinitionList`,
  `pf.Div`, `pf.Header`, …
- `pf.stringify(elem)` flattens an element to plain text.
- `elem.parent`, `elem.prev`, `elem.ancestor(n)` locate an element in context -
  e.g. `isinstance(elem.parent, pf.Doc)` for a top-level list, or
  `isinstance(elem.ancestor(3), pf.Doc)` for list items one level deep.

### The `Set` API

| Call | Effect |
| --- | --- |
| `set.add_question(title="", main_text=…)` | Start a new question. `main_text` takes a string or a panflute element; setting it again appends with a newline. |
| `set.current_question` | The question being built (`Question("INVALID")` before the first `add_question`, so stray calls are harmless). |
| `set.current_question.add_part_text(elem)` | Add a part, or fill the next part that has no text yet. |
| `set.current_question.add_solution(elem)` | Attach a worked solution. Spreads across parts that lack one; appends an empty part if every part already has a solution. |
| `set.current_question.parts.append(Part(text=…, worked_solution=…))` | Add a fully-formed part directly. |
| `set.increment_current_question()` | Move the "current" pointer forward - used while parsing a separate answers file. |

The exact spread/append rules are documented with runnable examples in the
docstrings of {meth}`~in2lambda.api.question.Question.add_part_text` and
{meth}`~in2lambda.api.question.Question.add_solution`.

### Two passes for separate answer files

When the user passes `-a answers.tex`, `runner()` in `in2lambda/main.py` runs
your filter a **second** time over the answers document with
`parsing_answers=True`. The usual pattern: on the first pass build questions and
parts; on the second pass call `set.increment_current_question()` when you reach a
new question's answers and `set.current_question.add_solution(...)` for each
solution. If answers only ever appear inline, ignore the flag.

### Annotated walkthrough: `PartsSepSol`

```python
# Only act on the top-level enumerate (not the nested parts list).
if isinstance(elem.parent, pf.Doc) and isinstance(elem, pf.OrderedList):
    for numbered_part in elem.content:            # one list item == one question
        if parsing_answers:
            set.increment_current_question()      # answers file: step to next question

        blurb, lettered_parts = [], []
        for section in numbered_part.content:
            match type(section):
                case pf.Para:                     # question stem
                    blurb.append(pf.stringify(section))
                case pf.OrderedList:              # (a), (b), (c) …
                    lettered_parts.extend(pf.stringify(i) for i in section.content)

        spaced_blurb = "\n\n".join(blurb or " ")

        if parsing_answers and not lettered_parts:
            set.current_question.add_solution(spaced_blurb)
        elif not parsing_answers:
            set.add_question(main_text=spaced_blurb)

        for part in lettered_parts:
            (set.current_question.add_solution(spaced_blurb + part)
             if parsing_answers
             else set.current_question.add_part_text(part))
```

## 6. Write the module docstring

`filter.py`'s module docstring **is** the filter's documentation - it's rendered
verbatim onto the auto-generated page next to the compiled example (see
[Writing Documentation](documentation)). Write it for someone choosing between
filters: a one-line summary of the structure, then a short paragraph on how
questions, parts and solutions are laid out and when to pick this filter.

## 7. Test it

Add the filter to the parametrised end-to-end suite:

```python
# tests/test_runner.py
BUILTIN_FILTERS = ["PartsSepSol", "PartsOneSol", "PartPartSolSol",
                   "PartSolPartSol", "MyFilter"]
```

That runs your `example` file through `runner()` and asserts both a populated
`Set` and importable JSON/zip. If your filter supports a separate answers file,
add a focused test alongside it that passes `answer_file=` to `runner()`.

## 8. Verify

```shell
$ poetry run in2lambda convert --help                       # MyFilter is listed
$ poetry run in2lambda convert in2lambda/filters/MyFilter/example.tex MyFilter -o ./out
$ poetry run pytest -k MyFilter
$ poetry run pytest                                         # nothing else regressed
$ poetry run pre-commit run --all-files                     # black / autoflake clean
$ sphinx-build -v docs/source docs/_build/html              # filter page builds
```

Open a `./out/set/question_*.json` and check `masterContent`, `parts[*].content`
and `parts[*].workedSolution.content` are populated as you expect.
