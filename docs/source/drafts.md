# 📝 Drafts

A draft is a JSON file beside a problem sheet. A draft names the markdown file the sheet was
converted to and holds that file's hash, the blocks the markdown is made of, one field per question, part
and solution, and the log of the commands that wrote those fields. `in2lambda convert` reads a document and writes a set in
one command. A draft is the other way of working: in2lambda converts the document once, and the
questions are then written, checked and rebuilt from the frozen markdown and the log.

This page walks one sheet through every step of that: freeze the document, fill the draft in from
a spec or by commands, check the draft over, and write the set. The sheet is `sheet.md`:

```markdown
# Pipe flow problems

Answer both questions, and show your working.

Q1. Water flows through a horizontal pipe of diameter $d$ at speed $v$.

(a) Find the volume flow rate. (4 marks)

Q2. A submarine is towed at speed $U$ through still water.

(a) Find the drag force on it.

## Solutions

The flow rate is $Q = \pi d^2 v / 4$.
The drag is $F = \half \rho U^2 A C_d$.
```

The first command below converts a `.docx` or a `.tex` sheet to markdown beside it, and every
command after that reads the markdown.

## Freeze the document

```bash
$ in2lambda source add sheet.md
Wrote /home/you/sheet/sheet.draft.json
```

`in2lambda source add` hashes the markdown and writes the draft beside it. The draft is named after the document, so a folder of sheets holds one draft per
sheet:

```bash
$ cat sheet.draft.json
{
  "fields": {},
  "log": [],
  "sources": [
    {
      "blocks": [
        {
          "end": 1,
          "id": "b1",
          "start": 1,
          "type": "heading"
        },
        {
          "end": 3,
          "id": "b2",
          "start": 3,
          "type": "paragraph"
        },
        {
          "end": 5,
          "id": "b3",
          "start": 5,
          "type": "paragraph"
        },
        {
          "end": 7,
          "id": "b4",
          "start": 7,
          "type": "list item"
        },
        {
          "end": 9,
          "id": "b5",
          "start": 9,
          "type": "paragraph"
        },
        {
          "end": 11,
          "id": "b6",
          "start": 11,
          "type": "list item"
        },
        {
          "end": 13,
          "id": "b7",
          "start": 13,
          "type": "heading"
        },
        {
          "end": 16,
          "id": "b8",
          "start": 15,
          "type": "paragraph"
        }
      ],
      "hash": "sha256:dd51e0597b0e2e091651223a1acebc6f3c694cea9abf61eba4faebace24782e5",
      "source": "sheet.md"
    }
  ]
}
```

A block is one element pandoc found - a heading, a paragraph, a list item - with the lines it
spans and an id to quote it by. A list item, or a `\begin{solution}` environment, holds elements
of its own, and each of those is a block too: `b3` holds `b3.1` and `b3.2`, and `b3` spans them.
[Specs](spec.md) says more about the nested ones. `fields` holds the questions, parts and solutions
written from the sheet, and `log` holds the commands that wrote them. Both are empty until a spec
or a command fills them in.

A line range requires that the text it refers to does not change. `in2lambda source add` records
the hash of the markdown in the draft. Every command that reads the draft hashes the markdown on
disk and compares it with the hash the draft holds, and refuses where the two differ, because
line 5 of an edited document is not the line the earlier commands were run against. `in2lambda source add --start-over` freezes
the document again and discards the draft written from it.

A draft records every command in its log as the command runs. `in2lambda draft replay` builds the
draft again from the frozen markdown and the log, reading nothing else, so a draft a model wrote
is rebuilt and checked without running the model again.

## Read the source back

```bash
$ in2lambda source show
b1   1  # Pipe flow problems
     2
b2   3  Answer both questions, and show your working.
     4
b3   5  Q1. Water flows through a horizontal pipe of diameter $d$ at speed $v$.
     6
b4   7  (a) Find the volume flow rate. (4 marks)
     8
b5   9  Q2. A submarine is towed at speed $U$ through still water.
    10
b6  11  (a) Find the drag force on it.
    12
b7  13  ## Solutions
    14
b8  15  The flow rate is $Q = \pi d^2 v / 4$.
    16  The drag is $F = \half \rho U^2 A C_d$.
```

`in2lambda source show` prints the frozen markdown numbered, with the id of each block against
the line it starts on. A block and the first block nested inside it start on the same line, so a
line may carry several ids, and the margin is indented two spaces for each level of nesting. A
command names a block by its id, `b3`, a line of the source, `s5`, or a range of lines, `s15:16`.

## Fill the draft in from a spec

A spec is a YAML file of selectors saying which blocks are questions, which are parts and which
are solutions. This sheet labels each question `Q1.`, `Q2.`, and the `question` selector matches
that label:

```yaml
question: Para text~'^Q\d+\.'
part:     ListItem
strip:    ['^Q\d+\. ']
ignore:   Header
layout:   PartsSepSol
```

```bash
$ in2lambda spec run spec.yaml
b2 (lines 3-3) is in no field and not marked ignore.
b8 (lines 15-16) is in no field and not marked ignore.
```

The spec writes the two questions, their parts and the two headings it was told to ignore.
`in2lambda spec run` then reports the two blocks the spec wrote no field from: the rubric, which
no selector matches, and the solutions, which this spec has no `solution` selector for. A spec run accounts for every block of
the document or names the blocks it left out.

Each field records where its value came from:

```json
{
  "q1.text": {
    "by": "you",
    "edited": false,
    "layer": 1,
    "ranges": [[5, 5]],
    "value": "Water flows through a horizontal pipe of diameter $d$ at speed $v$."
  }
}
```

`layer` says what wrote the field: 1 a spec, 2 a predicate the spec called, 3 a range of the
source quoted by a command, 4 a literal somebody typed. `ranges` are the lines of the frozen
markdown the value was copied from, and `by` is who ran the command. The value holds no `Q1. `,
because `strip` takes that label off the front of every value a selector matched. See
[specs](spec.md) for the selectors, the predicates and the layouts a spec is written from.

## Fill the draft in by commands

Where no spec fits the document, the commands write the same fields one at a time. A spec fills a
draft in once, so the draft starts again before they run:

```bash
$ in2lambda source add --start-over sheet.md
Wrote /home/you/sheet/sheet.draft.json
```

The title holds no question, so `in2lambda draft mark ignore` marks the title. Block `b3` is the
first question:

```bash
$ in2lambda draft mark ignore b1
Wrote b1.ignore.
$ in2lambda draft question add --text b3
Wrote q1.text.
```

Each command prints the key of the field it wrote, which is the key the next command names.
`question add` takes the first number no question has taken, and quotes the block into it:

```json
{
  "q1.text": {
    "by": "you",
    "edited": false,
    "layer": 3,
    "ranges": [[5, 5]],
    "value": "Q1. Water flows through a horizontal pipe of diameter $d$ at speed $v$."
  }
}
```

A command quotes the lines as the source writes them, so this `q1.text` holds the `Q1. ` the
sheet numbers the question with. The spec above took that label off with `strip`. in2lambda
records the command in the log as it applies it:

```json
{
  "args": {
    "text": "b3"
  },
  "by": "you",
  "command": "question add"
}
```

`by` is your username, or what `--by` gives it. A reader reads `by` to see whether a model or a
person wrote the field.

Line 7 gives the marks the first part is worth, which the field should not hold. So the part is
typed out rather than quoted, and `b4` is marked ignore, because no field accounts for it now:

```bash
$ in2lambda draft mark ignore b4
Wrote b4.ignore.
$ in2lambda draft part add q1 --literal 'Find the volume flow rate.'
Wrote q1.p1.text.
```

```json
{
  "q1.p1.text": {
    "by": "you",
    "edited": true,
    "layer": 4,
    "ranges": [],
    "value": "Find the volume flow rate."
  }
}
```

A literal is layer 4. No line of the source holds the wording, so the field's `ranges` is empty.
The field's `edited` is `true`.

The second question and its part are both quoted:

```bash
$ in2lambda draft question add --text b5
Wrote q2.text.
$ in2lambda draft part add q2 --text b6
Wrote q2.p1.text.
```

Pandoc reads `(a)` as a list marker, so `b6` is a list item, and a field quoted from a list item
is dedented by the item's own marker. `q2.p1.text` holds `Find the drag force on it.`

## Find the blocks in no field

```bash
$ in2lambda validate
b2 (lines 3-3) is in no field and not marked ignore.
Warning: q2.p1 (lines 11-11) has no solution: neither q2.p1.solution nor q2.solution is written.
b7 (lines 13-13) is in no field and not marked ignore.
b8 (lines 15-16) is in no field and not marked ignore.
Warning: q1.p1 has no solution: neither q1.p1.solution nor q1.solution is written.
```

`in2lambda validate` checks the draft over and writes what it finds into the draft as the draft's
report. Whoever is writing the draft reads that report to find the blocks in no field and the
questions with no solution. A finding at level error is the draft contradicting its own source:
lines nothing accounts for, two fields quoted from the same lines, a numbering with a hole in it,
maths Lambda Feedback will not render.
A question with no solution is reported at level warning, because many sheets write their
solutions in another file, and some sheets have none.

`in2lambda validate` prints the findings in the order of the source, and prints the findings
about no particular line last. `q1.p1` was typed out, so it names no lines.

## Mark the rubric and the Solutions heading ignored

The rubric and the Solutions heading are two of the blocks the report names, and neither holds a
question:

```bash
$ in2lambda draft mark ignore b2
Wrote b2.ignore.
$ in2lambda draft mark ignore b7
Wrote b7.ignore.
```

The sheet writes its two solutions on two lines with no blank line between them, so pandoc made
one paragraph of both and `b8` spans lines 15 to 16. `split block` cuts a block in two at the
line the second half starts on:

```bash
$ in2lambda draft split block b8 16
Wrote b8a and b8b.
```

The document is unchanged. `b8a` and `b8b` are blocks of the draft, quoted by their ids as any
other block is. `in2lambda draft replay` runs `split block b8 16` again from the log, and writes
the blocks `b8a` and `b8b` again. The two solutions are then quoted into the two questions:

```bash
$ in2lambda draft question solution q1 --text b8a
Wrote q1.solution.
$ in2lambda draft question solution q2 --text b8b
Wrote q2.solution.
```

## Change what a field says

The sheet writes the second solution with `\half`, which KaTeX does not define, and
`in2lambda validate` reports that against `q2.solution`. No line of the source writes the maths in
a command KaTeX defines, so the wording itself is changed:

```bash
$ in2lambda draft field replace q2.solution '\half' '\tfrac12'
Wrote q2.solution.
```

```json
{
  "q2.solution": {
    "by": "you",
    "edited": true,
    "layer": 3,
    "ranges": [[16, 16]],
    "value": "The drag is $F = \\tfrac12 \\rho U^2 A C_d$."
  }
}
```

The layer and the ranges are left as they were, so the field still names the lines it was quoted
from, and `edited` says the field no longer holds what those lines say. The wording replaced has
to occur in the field exactly once, and `--regex` reads it as a regular expression.

## Replay and check again

```bash
$ in2lambda draft replay
Replays as it stands.
```

`in2lambda draft replay` builds the draft again from the frozen markdown and the log, and
compares the result with the file byte for byte. `in2lambda draft replay` refuses where the
document has changed since in2lambda froze it, where the log names a command this version of
in2lambda has not got, and where somebody edited a field by hand.

A command that changes the draft deletes the draft's report, because the report described the
draft before the command ran. So the checks run again:

```bash
$ in2lambda validate
Nothing to report.
```

## Build and render

```bash
$ in2lambda build
Wrote /home/you/sheet/out/set.zip
```

`in2lambda build` writes the draft out as a Lambda Feedback set: `out/set.zip` and the files it
is zipped from. `in2lambda build` refuses a draft that `in2lambda validate` has not been run on
since the draft last changed, and refuses a draft whose report holds a finding at level error.
Where the report holds only findings at level warning, `in2lambda build` prints each finding as a
`Warning:` line and then writes `out/set.zip`. The fields become the
questions and parts of the export - see [the question format](question-format) for what the
export holds.

```bash
$ in2lambda render
Wrote /home/you/sheet/out/question_000_Question_1.pdf
Wrote /home/you/sheet/out/question_001_Question_2.pdf
```

`in2lambda render` writes one PDF per question, compiled the way Lambda Feedback's PDF generator
compiles it, which needs pandoc and [xelatex](https://tug.org/texlive/). `in2lambda render`
writes the PDFs whatever the draft's report holds. A reader reads the PDFs to check a draft
before fixing it.

`out/set.zip` is imported as [the quickstart](quickstart) describes, under "Import into Lambda
Feedback".
