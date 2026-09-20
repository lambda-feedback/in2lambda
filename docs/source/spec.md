# 📐 Specs

A spec is a small YAML file saying which blocks of a document are questions, which are parts and
which are solutions. Running one fills in the draft beside the document, so that the wording of
every question comes out of the source rather than being retyped:

```bash
$ in2lambda source add questions.docx
$ in2lambda spec run spec.yaml
b6 is in no field.
```

The last line is the point of it: a spec run reports every block it made nothing of, so what is
left to account for is in front of you rather than quietly missing.

## What a spec says

```yaml
question: Header level=2 text~'^Question'
part:     ListItem
solution: after Header text=Solutions, label~'^\d+(\([a-z]\))?$'
strip:    ['^#+ ', '^\([a-z]\) ', '^\d+(\([a-z]\))? ']
ignore:   Header level=1
layout:   PartsSepSol
```

`question` and `layout` have to be there; `part`, `solution`, `strip` and `ignore` need not be.

- **`question`, `part`, `solution`** select the blocks that are each of those things.
- **`ignore`** selects the blocks that are none of them - a running header, a page of
  instructions - and marks them as `in2lambda draft mark ignore` would, so they are not reported
  as left out.
- **`strip`** is a list of patterns taken off the front of every value: the `(a) ` or `1. ` that
  labels a part in the document, but not in the question.
- **`layout`** is one of the [filters](filters/index), and says which solution answers which
  question or part. See below.

A block is whatever the first of `ignore`, `question`, `part`, `solution` to match it says it is,
so a spec whose selectors overlap is read in the order it is written down.

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

Each question is `q1`, `q2` and so on in the order they appear, and each of its parts `q1.a`,
`q1.b`. So a spec fills in `q1.text`, `q1.a.text`, `q1.a.solution` and, for a question answered
as a whole, `q1.solution`. Every one of them records the lines it was copied from, and that a
spec wrote it.

The spec is recorded in the draft's log with its hash, so `in2lambda draft replay` rebuilds the
same draft from the same spec - and refuses if the spec has been edited since, because then it
would be checking the draft against something else.
