# One document down both routes

Each folder here takes one document through the draft workflow - `source add`, a spec or a
run of commands, `validate`, `build` - and compares the set in the zip with the set
`in2lambda convert` makes of the same document. The two routes are otherwise tested
against fixtures of their own, and neither test says whether they agree.

A folder named after a filter is about the `example.tex` that filter ships, converted with
that filter. Any other folder is named after a folder of `fixtures/sources`, and is
converted with `PartsOneSol`. A folder holding a `spec.yaml` fills the draft in by running
that spec; a folder holding a `commands.json` applies each command in it in order. To
cover another document, add a folder: no test names any of them.

The line ranges in a `commands.json` are lines of the markdown pandoc writes, not of the
document itself, as the ranges in `fixtures/sources` are. They were produced with
**pandoc 3.9.0.2**.

## What the comparison ignores

The comparison is of each question's main text and of each part's text. Four differences
between the routes are not differences in what a question says, and are taken off both
sides before comparing:

- **Line breaks.** The draft quotes the lines pandoc wrapped; convert writes a paragraph
  on one line. Every run of whitespace is compared as one space.
- **Image references.** Convert writes every image as `![pictureTag](path)`; the draft keeps
  the alt text the document wrote, which is empty for `\includegraphics`. The set read back
  from the zip names each file as it sits in the export's `media/`, where the set convert
  returns holds the path the document wrote. Both sides are compared by the file's name.
- **A lone empty part.** A question the draft writes without parts exports as one part with
  nothing in it, because Lambda Feedback's template fills a question holding no part with
  placeholder wording. Convert writes no part at all. A single part with no text is
  dropped from both.
- **Typographic quotes.** Pandoc's LaTeX reader writes `’` where its `commonmark_x` writer
  writes `'`, so `aren’t` reaches convert and `aren't` reaches the draft. Both are folded
  to the ASCII quotes.

Worked solutions are not compared. The `PartsOneSol` filter matches a solution environment
only when the Div's first element stringifies to `Solution`, which pandoc never writes, so
convert drops every worked solution in that layout (t52). `PartsSepSol`'s example, and the
three source documents, write no solution at all. `test_the_draft_holds_the_solutions_convert_drops`
asserts on the draft side that the two solution environments of `PartsOneSol/example.tex`
reach `q1.solution` and `q2.solution`.

## Which layouts are here

`PartsOneSol` and `PartsSepSol`. The `PartPartSolSol` and `PartSolPartSol` examples nest
each question's parts and their solutions inside one top-level list item, which is one
block of the frozen source: no selector reaches inside it (t51), and no draft command
writes a `qN.pM.solution` (t53). Add a folder for each of those layouts when both land.

## What does not run yet

`docx` is not compared. `in2lambda.filters.markdown.image_directories` opens the document
as UTF-8 text to look for a `\graphicspath`, so `in2lambda convert` raises a
`UnicodeDecodeError` over any .docx that holds an image. The comparison reports that
folder as an expected failure naming the cause, and compares the two routes as soon as
convert reads the document. The folder's draft is still built, exported and replayed.

`PartsOneSol/spec.yaml` quotes the solution environment holding `$$1+1 = 2$$`, which
`source add` freezes on one line and `in2lambda validate` reports as an error (t44), so
`build` refuses the draft. The test probes for that rather than naming the folder: it
freezes a source of display maths, and skips a folder whose report holds the same finding.
The folder runs unchanged once t44 writes display maths in block form.
