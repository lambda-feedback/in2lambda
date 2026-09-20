# Specs run over a source

Each folder here is one run of `in2lambda spec run`: a `source.md` to freeze, the `spec.yaml` to
run over it, the `expected.json` the spec should leave in the draft's `fields`, and the
`uncovered.txt` of the blocks the command should report as being in no field. The test freezes
the source, runs the spec, compares both, and then replays the draft from its log and checks the
file is unchanged byte for byte - so a folder covers what a spec makes of a document and that it
can be rebuilt from what was recorded.

To cover another kind of document, add a folder. There is one per layout, since a layout is
only a rule about which solution answers which question or part: `parts_one_sol` has one
solution to each question, `part_sol_part_sol` a solution after each part, `part_part_sol_sol`
the parts and then their solutions in order, and `parts_sep_sol` every solution together at the
end. `parts_sep_sol` is the spec from the ticket, and leaves its `## Solutions` heading in no
field, which is what a coverage report is for.

Each document is one the other three layouts read differently - a question with two parts and
one solution, or with a part nobody answered - since a document every layout agrees about
would pin no rule, and a layout given the wrong rule would go on passing.

`predicates` is the other thing a folder can pin: its spec names a `predicates.py` beside it and
calls functions from it, because what tells its questions from the paragraph about marks is the
bold each of them starts with, which is markup rather than text. Its log entry names that file
and hashes it as it does the spec, which is what makes a changed predicate refuse to replay.

A selector matches what pandoc parses, and a field holds the markdown of the lines it was taken
from, dedented where those lines are a list item's: `numbered_questions` is the sheet whose
questions are written `1.  ` and run on over several lines, and its spec strips nothing but the
`Solution: `, so it pins that the marker and the indent under it come off by themselves. That
is why no spec here strips a `(a) ` - pandoc reads `(a)` as a list marker - while the `Q1. `
and the `Solution: `, which it does not, are still `strip`'s to take off.
