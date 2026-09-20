# 📐 Specs

A spec is a small YAML file saying which blocks of a document are questions, which are parts and
which are solutions. Running one fills in the draft beside the documents it was frozen from, so
that the wording of every question comes out of the source rather than being retyped:

```bash
$ in2lambda source add questions.docx solutions.docx
$ in2lambda spec run spec.yaml
b6 (lines 12-13) is in no field and not marked ignore.
```

The last line is the point of it: a spec run reports every block it made nothing of, naming the
lines it is, so what is left to account for is in front of you rather than quietly missing.

The fields a draft holds belong to the spec that wrote them, so a spec is run over a draft once.
Running an edited one again is refused; freeze the document afresh and run it, which is two
commands:

```bash
$ in2lambda source add --start-over questions.docx solutions.docx
$ in2lambda spec run spec.yaml
```

## What a spec says

```yaml
question: Header level=2 text~'^Question'
part:     ListItem
solution: after Header text=Solutions, label~'^\d+(\([a-z]\))?$'
strip:    ['^#+ ', '^\d+(\([a-z]\))? ']
ignore:   Header level=1
layout:   PartsSepSol
```

`question` and `layout` have to be there; `part`, `solution`, `strip`, `ignore` and
`predicates` need not be.

- **`question`, `part`, `solution`** select the blocks that are each of those things.
- **`ignore`** selects the blocks that are none of them - a running header, a page of
  instructions - and marks them as `in2lambda draft mark ignore` would, so they are not reported
  as left out.
- **`strip`** is a list of patterns taken off the front of every value: the `Q1. ` or
  `Solution: ` that labels a block in the document, but not in the question. A list marker is
  not one of them, since a value quoted out of a list item arrives dedented.
- **`predicates`** names a Python file beside the spec, for the selectors that cannot say what
  they mean in constraints alone. See below.
- **`layout`** is one of the [filters](filters/index), and says which solution answers which
  question or part. See below.

A block is whatever the first of `ignore`, `question`, `part`, `solution` to match it says it is.
That order is fixed, whatever order the keys are written in, so a spec whose selectors overlap
has to tell them apart by what they match rather than by where they are in the file.

`question`, `part`, `solution` and `ignore` each take one selector, or a list of them written
under the key. A block has that role where any one of the selectors in the list matches it, so
one spec selects the questions of a document that writes them two different ways:

```yaml
ignore:
  - Header level=1
  - Para text~'^Marks'
```

## Selectors

A selector is a block type, then any number of constraints:

```
[after SELECTOR,] [Type] name=value name~'regex' ...
```

The type is a pandoc element - `Header`, `Para`, `ListItem` - and may be left out to match any
block. A constraint is about one of four things:

| Attribute | What it is |
|-----------|------------|
| `level`   | A heading's level: `level=2` is `##`. |
| `text`    | The whole block as text, with the markup taken off. |
| `label`   | The first word of that text, which is usually what numbers a question. |
| `depth`   | How deep the block sits: `depth=1` is a top-level element of the document, `depth=2` a block nested inside one. See **Nested blocks** below. |

`=` asks for exactly that; `~` for a regular expression anywhere in it. `after SELECTOR,` says
the block has to come after the first block that selector matches, which is how the solutions at
the end of a problem sheet are told apart from the questions at the front.

A regular expression goes in single quotes. YAML reads `\(` inside double quotes as an escape
and complains, and `'^\([a-z]\)'` is the same string without the argument.

A selector matches what **pandoc** makes of the document, while a field holds the **markdown** of
the lines it came from. That is worth knowing where a part is written `(a) Find the load.`: it is
a `ListItem`, because pandoc reads `(a)` as a list marker, and the value comes dedented the way
pandoc reads the item - the marker off the first line and as much of the same width off every
line under it - so `strip` is only for what pandoc does not read as a marker, the `Q1. ` and the
`Solution: `.

## Nested blocks

Many sheets are written as one list: each question is an item, and the parts of a question are a
list nested inside that item. `in2lambda source add` records the blocks inside a block as well as
the top-level ones, so that a selector reaches a part.

A list item and a fenced div - what pandoc makes of a `\begin{solution}` environment - are the
two blocks that hold blocks of their own. One holding a single element other than a list is that
element and stays one block. A nested block's id is the id of the block holding it and a number:
`b3` holds `b3.1` and `b3.2`, and `b3.2` holds `b3.2.1`. `in2lambda source show` prints the ids
against the line each block starts on, indented two spaces for each level below the top.

A block spans the blocks nested inside it, so `depth` is what tells a question from its parts:

```yaml
question: Para depth=2
part:     Para depth=3
solution: Div
layout:   PartSolPartSol
```

That spec reads a sheet whose questions are top-level items. The question is the item's own
paragraph, `b3.1`, rather than the whole item `b3`, and `after` still pairs a solution with the
part above it.

A block whose children hold a role holds none itself. Writing `b3` into `q1.text` and `b3.2`
into `q1.p1.text` would be two fields quoted from the same lines, which no command writes: a
spec quotes the item's own paragraphs into the question and the nested items into the parts. So
one selector may match a block and its children both, and the block steps aside for them.

A fenced div's lines are the ones its content stands on. The `:::` lines pandoc wrote around it
are pandoc's, as a list marker is, and no field quotes them.

A block with children is not reported as being in no field. Its children are reported instead,
because a parent spans the blank lines and fences between them, which nothing can quote.

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

A sheet holding more solutions than the layout has questions and parts to answer sends two of
them to the one field. The second is left in no field and reported, naming the field and the
block that holds it. The section below says the same of a document of solutions.

## A separate solutions document

Many sheets come as two files: the questions, and the solutions written separately from them.
Freeze both, in that order, and the draft holds them as source 1 and source 2. A file can be
added to a draft later just as well, which freezes it as the next source:

```bash
$ in2lambda source add questions.docx
$ in2lambda source add solutions.docx
```

`in2lambda source show` then prints each source under its number and its name, and everything
that names a block or a line range says which source it means. `b3` and `s10:14` are the first
source's, as they have always been; `2/b3` and `2/s14:20` are the second's, and `1/b3` is `b3`
the long way round. A field quoted from a source after the first records that source's number
beside the lines it came from, since line 5 of the solutions is not line 5 of the sheet.

The same spec runs over every source, and each selector matches within the source it is being
run over - `after Header text=Solutions` is about where a block sits in its own document. What
changes is what the selectors mean in a document of solutions, which is what `in2lambda convert
-a` makes of an answers file:

- A block the **`question`** selector matches is a **marker** - the `Q2.` written above the
  solutions to the second question. It answers nothing itself, is marked ignored, and sends what
  follows it to that question's first slot.
- A block the **`part`** or the **`solution`** selector matches is a **solution**, and they take
  the slots in order: each question's parts, or the question itself where it has none.
- The **`layout`** is the sheet's, and says nothing about the documents after it. Solutions
  written separately come in the order the questions do, which is the `PartsSepSol` rule whatever
  the sheet itself is laid out as.

A solution past the last slot is reported as being in no field, like any other block the spec
made nothing of. So is one landing on a question the solutions before it have answered, with a
second line naming the field it would have gone in and the block that holds it:

```
b7 (lines 14-15) is in no field and not marked ignore.
b7 (lines 14-15) would be q2.solution, which b5 (lines 10-11) already holds.
```

The run writes every other field, so a spec that sends two solutions to one field still fills
the draft in and names the block to look at.

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
