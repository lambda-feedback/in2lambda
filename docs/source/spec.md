# 📐 Specs

A spec is a small YAML file saying which blocks of a document are questions, which are parts and
which are solutions. Running one fills in the draft beside the document, so that the wording of
every question comes out of the source rather than being retyped:

```bash
$ in2lambda source add questions.docx
$ in2lambda spec run spec.yaml
b6 (lines 12-13) is in no field and not marked ignore.
```

The last line is the point of it: a spec run reports every block it made nothing of, naming the
lines it is, so what is left to account for is in front of you rather than quietly missing.

The fields a draft holds belong to the spec that wrote them, so a spec is run over a draft once.
Running an edited one again is refused; freeze the document afresh and run it, which is two
commands:

```bash
$ in2lambda source add --start-over questions.docx
$ in2lambda spec run spec.yaml
```

## What a spec says

```yaml
question: Header level=2 text~'^Question'
part:     ListItem
solution: after Header text=Solutions, label~'^\d+(\([a-z]\))?$'
strip:    ['^#+ ', '^\([a-z]\) ', '^\d+(\([a-z]\))? ']
ignore:   Header level=1
layout:   PartsSepSol
```

`question` and `layout` have to be there; `part`, `solution`, `strip`, `ignore` and
`predicates` need not be.

- **`question`, `part`, `solution`** select the blocks that are each of those things.
- **`ignore`** selects the blocks that are none of them - a running header, a page of
  instructions - and marks them as `in2lambda draft mark ignore` would, so they are not reported
  as left out.
- **`strip`** is a list of patterns taken off the front of every value: the `(a) ` or `1. ` that
  labels a part in the document, but not in the question.
- **`predicates`** names a Python file beside the spec, for the selectors that cannot say what
  they mean in constraints alone. See below.
- **`layout`** is one of the [filters](filters/index), and says which solution answers which
  question or part. See below.

A block is whatever the first of `ignore`, `question`, `part`, `solution` to match it says it is.
That order is fixed, whatever order the keys are written in, so a spec whose selectors overlap
has to tell them apart by what they match rather than by where they are in the file.

## Selectors

A selector is a block type, then any number of constraints:

```
[after SELECTOR,] [Type] name=value name~'regex' ...
```

The type is a pandoc element - `Header`, `Para`, `ListItem` - and may be left out to match any
block. A constraint is about one of three things:

| Attribute | What it is |
|-----------|------------|
| `level`   | A heading's level: `level=2` is `##`. |
| `text`    | The whole block as text, with the markup taken off. |
| `label`   | The first word of that text, which is usually what numbers a question. |

`=` asks for exactly that; `~` for a regular expression anywhere in it. `after SELECTOR,` says
the block has to come after the first block that selector matches, which is how the solutions at
the end of a problem sheet are told apart from the questions at the front.

A regular expression goes in single quotes. YAML reads `\(` inside double quotes as an escape
and complains, and `'^\([a-z]\)'` is the same string without the argument.

A selector matches what **pandoc** makes of the document, while a field holds the **markdown** of
the lines it came from. That is worth knowing in two places: a part written `(a) Find the load.`
is a `ListItem`, because pandoc reads `(a)` as a list marker, and `strip` still has to take the
`(a) ` off the front of the value, because the line it was copied from still has it.

## Predicates

Some documents cannot be told apart by their text. If the questions are the paragraphs written
in bold, and a paragraph about marking starts with the word `Question` as surely as they do,
then no `text~` constraint will do it. For those, a spec names a Python file beside it and calls
functions from it:

```yaml
predicates: predicates.py
question:   Para bold_lead()
solution:   Para italic_lead()
layout:     PartsOneSol
```

A `name()` anywhere in a selector is a call, and goes with a type, with constraints and with
`after` - `after Header text=Solutions, is_solution()` - all of which have to hold as well. A
predicate is an ordinary function of one argument, the [panflute](https://scorreia.com/software/panflute/)
element the block is, that says whether the block is one of those:

```python
import panflute as pf


def bold_lead(element: pf.Element) -> bool:
    """Whether a block begins in bold."""
    first = element.content[0] if element.content else None
    while isinstance(first, pf.Span) and first.content:  # Past the sourcepos spans.
        first = first.content[0]
    return isinstance(first, pf.Strong)
```

The frozen source is parsed with pandoc's `sourcepos`, so that each block knows which lines it
came from, and that leaves every inline wrapped in a `Span` carrying where it is. A predicate
looking at the markup has to see through them, as the one above does.

The file is named in the draft's log with its hash, exactly as the spec is, and it is run from
the bytes that hash was taken of. So a predicate edited after a run is refused the same way an
edited spec is, by `in2lambda draft replay` and by running the spec again.

## Layouts

The layout is the one thing that differs between problem sheets that are otherwise alike: where
the solutions are, and what each of them answers.

| Layout | Which solution answers what |
|--------|-----------------------------|
| `PartsOneSol` | One solution to the whole question, however many parts it has. |
| `PartSolPartSol` | Each solution answers the part just before it, or the question if it has no parts yet. |
| `PartPartSolSol` | The parts come together and their solutions come after, in the same order. |
| `PartsSepSol` | Every solution is at the end: the first answers the first part of the first question, and so on. |

## What it writes

Each question is `q1`, `q2` and so on in the order they appear, and each of its parts `q1.p1`,
`q1.p2`. So a spec fills in `q1.text`, `q1.p1.text`, `q1.p1.solution` and, for a question
answered as a whole, `q1.solution`. They are the names the `in2lambda draft` commands give out
as well, so a draft filled in either way is the same draft. Every one of them records the lines it was copied from, and that a
spec wrote it.

The spec is recorded in the draft's log with its hash, so `in2lambda draft replay` rebuilds the
same draft from the same spec - and refuses if the spec has been edited since, because then it
would be checking the draft against something else. That is why running an edited spec over a
draft it has already filled in is refused too: the draft would be left holding fields no spec on
disk wrote, and no replay could ever check it again.
