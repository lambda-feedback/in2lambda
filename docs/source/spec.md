# 📐 Specs

A spec is a YAML file that says which blocks of a document are questions, which are parts and
which are solutions. `in2lambda spec run` fills in the draft beside the documents the spec was
frozen from, copying the wording of every question out of the source:

```bash
$ in2lambda source add questions.docx solutions.docx
$ in2lambda spec run spec.yaml
b6 (lines 12-13) is in no field and not marked ignore.
```

The last line illustrates the purpose of a spec. Blocks not matched to a field are reported, with
their line numbers, so that all content is accounted for.

The fields of a draft belong to the spec that wrote them, so a spec runs over a draft once.
`in2lambda spec run` refuses an edited spec over a draft it has already filled in. Freeze the
documents again and run the spec, which takes two commands:

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

A spec must set `question` and `layout`. A spec may set `part`, `solution`, `strip`, `ignore` and
`predicates`.

- **`question`, `part`, `solution`** select the blocks that are questions, parts and solutions.
- **`ignore`** selects the blocks that are none of those three, such as a running header or a page
  of instructions. `in2lambda spec run` marks each one as `in2lambda draft mark ignore` does, so
  that the run does not report it.
- **`strip`** lists the patterns removed from the front of every value, such as the `Q1. ` or
  `Solution: ` that labels a block in the document but not in the question. A list marker is not
  one of those patterns, because a value quoted out of a list item is already dedented.
- **`predicates`** names a Python file beside the spec, for the selectors that constraints alone
  cannot express. See [Predicates](#predicates).
- **`layout`** is one of the [filters](filters/index), and assigns each solution to a question or
  part. See [Layouts](#layouts).

`in2lambda spec run` classifies a block as the first of `ignore`, `question`, `part` and
`solution` that matches it. That order is fixed, whatever order the keys are written in. A spec
whose selectors overlap must tell them apart by what they match.

`question`, `part`, `solution` and `ignore` each take one selector, or a list of selectors
written under the key. A block has that role where any one of those selectors matches the block,
so one spec selects the questions of a document that writes its questions two ways:

```yaml
ignore:
  - Header level=1
  - Para text~'^Marks'
```

## Selectors

A selector is a block type followed by any number of constraints:

```
[after SELECTOR,] [Type] name=value name~'regex' ...
```

The type is a pandoc element: `Header`, `Para`, `ListItem`. A selector that omits the type matches
any block. A constraint names one of four attributes:

| Attribute | Meaning |
|-----------|---------|
| `level`   | A heading's level. `level=2` matches `##`. |
| `text`    | The whole block as text, with the markup removed. |
| `label`   | The first word of that text, which usually numbers a question. |
| `depth`   | How deep the block sits. `depth=1` matches a top-level element of the document, `depth=2` a block nested inside one. See [Nested blocks](#nested-blocks). |

`=` matches the whole value. `~` matches a regular expression anywhere in the value. `after
SELECTOR,` requires the block to follow the first block that the named selector matches, which is
how a spec tells the solutions at the end of a problem sheet from the questions at the front.

A comma separates the `after` clause from the rest of the selector only outside quotes. A comma
inside a quoted pattern, such as `Para text~'^(Sheet|Note),|^Marks'`, is part of the pattern. One
line holds one selector: write two selectors as a list under the key, as above.

Write a regular expression in single quotes. YAML reads `\(` inside double quotes as an escape
sequence and reports an error, and single quotes pass the backslash through.

A selector matches the document as **pandoc** parses it, and a field holds the **markdown** of the
lines the block came from. A part written `(a) Find the load.` is a `ListItem`, because pandoc
reads `(a)` as a list marker. Its value is dedented as pandoc reads the item: the marker comes off
the first line, and the same width of indentation off every line below it. Use `strip` for the
labels pandoc does not read as a marker, such as `Q1. ` and `Solution: `.

(nested-blocks)=
## Nested blocks

Many sheets are written as one list: each question is an item, and the parts of a question are a
list nested inside that item. `in2lambda source add` records the blocks inside a block as well as
the top-level blocks, so that a selector reaches a part.

A list item and a fenced div, which is what pandoc writes a `\begin{solution}` environment as, are
the two blocks that hold blocks of their own. A list item or div holding a single element other
than a list is that element, and stays one block. A nested block's id is the id of the block
holding it and a number: `b3` holds `b3.1` and `b3.2`, and `b3.2` holds `b3.2.1`. `in2lambda source
show` prints the ids against the line each block starts on, indented two spaces for each level
below the top.

A block spans the blocks nested inside it, so `depth` distinguishes a question from its parts:

```yaml
question: Para depth=2
part:     Para depth=3
solution: Div
layout:   PartSolPartSol
```

That spec reads a sheet whose questions are top-level list items. The question is the item's own
paragraph `b3.1`, and not the whole item `b3`. The `PartSolPartSol` layout pairs each solution
with the part written above it.

A block whose children hold a role holds no role itself. Writing `b3` into `q1.text` and `b3.2`
into `q1.p1.text` would be two fields quoted from the same lines, which no command writes. A spec
quotes the item's own paragraphs into the question and the nested items into the parts. So one
selector may match a block and its children, and in2lambda assigns the role to the children.

A fenced div spans the lines its content is written on. The `:::` lines pandoc wrote around the
content are pandoc's, as a list marker is, and no field quotes them.

`in2lambda validate` reports the children of a block with children, in place of the block itself,
as being in no field. A block with children spans the blank lines and the fences between those
children, and no field can quote those lines.

(predicates)=
## Predicates

Some documents cannot be classified by their text. If the questions are the paragraphs written in
bold, and a paragraph about marking also starts with the word `Question`, no `text~` constraint
separates them. A spec then names a Python file beside it and calls functions from that file:

```yaml
predicates: predicates.py
question:   Para bold_lead()
solution:   Para italic_lead()
layout:     PartsOneSol
```

A `name()` anywhere in a selector calls a predicate. A call combines with a type, with constraints
and with `after` — `after Header text=Solutions, is_solution()` — and every one of them must hold.
A predicate is a function of one argument, the [panflute](https://scorreia.com/software/panflute/)
element for the block, that returns whether the selector matches:

```python
import panflute as pf


def bold_lead(element: pf.Element) -> bool:
    """Whether a block begins in bold."""
    first = element.content[0] if element.content else None
    while isinstance(first, pf.Span) and first.content:  # Past the sourcepos spans.
        first = first.content[0]
    return isinstance(first, pf.Strong)
```

`in2lambda source add` parses the frozen source with pandoc's `sourcepos`, so that each block
records the lines it came from. `sourcepos` wraps every inline element in a `Span` holding that
element's position, and a predicate reading the markup must look through those spans, as
`bold_lead` above does.

The draft's log names the predicate file with its hash, as it names the spec, and `in2lambda spec
run` runs the file from the bytes that hash was taken of. `in2lambda draft replay` and a second
`in2lambda spec run` refuse a predicate file edited since the first run, as they refuse an edited
spec.

(layouts)=
## Layouts

The layout says where the solutions are written and which question or part each one
answers. Problem sheets that are otherwise alike differ in their layout.

| Layout | Which solution answers what |
|--------|-----------------------------|
| `PartsOneSol` | One solution answers the whole question, however many parts it has. |
| `PartSolPartSol` | Each solution answers the part before it, or the question where no part precedes it. |
| `PartPartSolSol` | The parts come together and their solutions follow, in the same order. |
| `PartsSepSol` | Every solution is at the end. The first answers the first part of the first question, and so on. |

A sheet holding more solutions than the layout has questions and parts to answer sends two of
them to the one field. The second is left in no field and reported, naming the field and the
block that holds it. The section below says the same of a document of solutions.

## A separate solutions document

Many sheets come as two files: the questions, and the solutions written separately. Freeze both,
in that order, and the draft holds them as source 1 and source 2. `in2lambda source add` also adds
a file to an existing draft, which freezes that file as the next source:

```bash
$ in2lambda source add questions.docx
$ in2lambda source add solutions.docx
```

`in2lambda source show` prints each source under its number and its name, and every block id and
line range names the source it belongs to. `b3` and `s10:14` name the first source, `2/b3` and
`2/s14:20` the second, and `1/b3` names the block `b3` names. A field quoted from a source after
the first records that source's number beside the lines it was copied from, because line 5 of the
solutions is not line 5 of the sheet.

`in2lambda spec run` runs the same spec over every source, and each selector matches within the
source being run over: `after Header text=Solutions` names a position in one document. The
selectors mean something different in a document of solutions, the document `in2lambda convert
-a` reads as an answers file:

- A block the **`question`** selector matches is a **marker**, such as the `Q2.` written above the
  solutions to the second question. A marker answers nothing. `in2lambda spec run` marks the
  marker ignored and assigns the blocks after it to that question's first slot.
- A block the **`part`** or **`solution`** selector matches is a **solution**. Solutions fill the
  slots in order: each question's parts, or the question itself where it has no parts.
- The **`layout`** describes the sheet, and describes no document after it. Solutions written
  separately follow the order of the questions, which is the `PartsSepSol` rule, whatever layout
  the sheet uses.

`in2lambda spec run` reports a solution past the last slot as being in no field, like any other
unmatched block. `in2lambda spec run` reports a solution assigned to a question that an earlier
solution has answered in the same way, and adds a second line naming the field the solution
would have been written to and the block already written there:

```
b7 (lines 14-15) is in no field and not marked ignore.
b7 (lines 14-15) would be q2.solution, which b5 (lines 10-11) already holds.
```

`in2lambda spec run` writes every other field, so a spec that sends two solutions to one field
fills the draft in and names the block to read.

## What a spec writes

The questions are `q1`, `q2` and so on in the order they appear, and the parts of a question are
`q1.p1`, `q1.p2`. A spec fills in `q1.text`, `q1.p1.text`, `q1.p1.solution` and, for a question
answered as a whole, `q1.solution`. The `in2lambda draft` commands write the same names, so a
draft filled in either way holds the same fields. Each field records the lines it was copied from
and that a spec wrote it.

The draft's log names the spec with its hash, so `in2lambda draft replay` rebuilds the same draft
from the same spec. `in2lambda draft replay` refuses a spec edited since the run, because the spec
on disk describes a different draft. `in2lambda spec run` refuses an edited spec over a draft it
has already filled in for the same reason: the draft would hold fields that no spec on disk wrote,
and no replay could check it again.
