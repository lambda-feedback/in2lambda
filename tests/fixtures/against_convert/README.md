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

Each question's main text is compared, and each part's text and worked solution. Three
differences between the routes are not differences in what a question says, and are taken
off both sides before comparing:

- **Line breaks.** The draft quotes the lines pandoc wrapped; convert writes a paragraph
  on one line. Every run of whitespace is compared as one space.
- **Image references.** Convert writes every image as `![pictureTag](path)`; the draft keeps
  the alt text the document wrote, which is empty for `\includegraphics`. The set read back
  from the zip names each file as it sits in the export's `media/`, where the set convert
  returns holds the path the document wrote. Both sides are compared by the file's name.
- **A lone empty part.** A question the draft writes without parts or solution exports as
  one part with nothing in it, because Lambda Feedback's template fills a question holding
  no part with placeholder wording. Convert writes no part at all. A single part holding
  neither text nor a worked solution is dropped from both.

## Where the two routes differ today

A folder holding a `differs.txt` is a document the two routes make different sets of. Each
line is one difference, worded as the comparison words it - the question, the part, the
field, and what each route says there - with the ticket that would close it after `  # `.
A folder with no such file is a document the two routes say the same thing about.

Finding a difference the file does not list fails the test, and so does agreeing where it
lists one: closing a ticket below means deleting the lines it names.

- **t53** - no draft command writes a `qN.pM.solution`, and no selector reaches inside the
  top-level `\item` that `PartPartSolSol/example.tex` and `PartSolPartSol/example.tex`
  nest each part's solution in, so those lines are marked ignore and the draft answers
  neither part. `in2lambda.draft.export` already reads such a field, and
  `fixtures/specs/part_part_sol_sol` shows a spec writing one where the source is not
  nested.
- **Smart quotes** - pandoc's LaTeX reader writes `’` where its `commonmark_x` writer
  writes `'`, so convert uploads `aren’t` for `PartsOneSol/example.tex` and the draft
  uploads `aren't`.
