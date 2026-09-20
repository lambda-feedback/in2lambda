# Drafts built by commands

Each folder here is one run: a `source.md` to freeze, the `commands.json` to apply to the draft
of it, the `expected.json` those commands should leave in the draft's `fields`, and the
`report.json` that `in2lambda validate` should then find in it - a folder with no `report.json`
is a draft with nothing wrong with it, and one whose findings are all at level `warning` is a
draft `in2lambda build` says them over and exports anyway, where a `level` of `error` refuses
it. A folder holding a `solutions.md` beside its `source.md` is a sheet written as two
documents, and the solutions are frozen as the draft's second source, whose blocks and lines
are named `2/b3` and `2/s14`. The test freezes the sources, applies each command, checks
the draft over, compares the fields and the report, and then replays the draft from its log and
checks the file is unchanged byte for byte - so a folder covers both what a command writes and
that it can be rebuilt from what it recorded.

To cover another command or another check, add a folder. `mark_ignore` is the `sources/markdown`
document with two of its blocks marked as nothing to take a question from, and the other five
reported as in no field. `two_questions` is a sheet with a title, a rubric, two questions with a
part each and a separate solutions section, written out by every command there is, and it is the
clean one: the second question runs into its part with no blank line between them, so the parser
makes one block of the two and `split block` cuts it, and the first question's part is typed out
rather than quoted, because the source writes it with an `(a)` the field should not carry - which
is why the block it was typed from is marked ignore rather than left unaccounted for.
`field_replace` is a sheet the OCR left a brace out of the maths of: one `field replace` puts the
brace back and another, with `--regex`, writes a `\tfrac` over the division in the solution, so
both fields end up edited while their ranges still name the lines they were quoted from, and the
backslash in what the second one writes is written rather than read as a replacement template.
`part_without_solution` and `empty_field` are the smallest drafts the other two checks have
anything to say about; an overlap and a gap in the numbering are not here, because no run of
commands can make one. `figure_in_a_question` is a question whose text runs on into an image, so
the field quotes the reference and `figure.png` beside the source is what the export has to carry
into `media/`. `figure_in_a_folder` is the same question with the figure kept in a `figures/`
folder, as a sheet usually keeps its figures: the field quotes `figures/figure.png`, and the export
carries the file into `media/` and rewrites the reference to the name it is called there, since
that name is all Lambda Feedback looks one up by. Those two are the only folders here with a file
the fields point at.
`question_solution_beside_part_solutions` is the only one filled in by a spec rather than by
commands one at a time, and the only one whose question has two parts: both are answered by the
spec's own solutions, so the `question solution` after it answers nothing, and the export carries
it as a part of its own rather than dropping the wording. `nested_list` is a numbered question with two lettered parts nested inside it, quoted by line
range because only the top-level item is a block: each field is dedented by its own depth, four
spaces for the question and eight for the parts, while its range still names the source lines.
`question_without_parts` is a question
and nothing else, which the checks warn has no solution: it is here because a question with
no parts is what the export has to write out as an empty part rather than as the template's.
`questions_only` is the sheet half the corpus is - a title, two questions, two parts under the
first of them and no solution written anywhere - so every one of its findings is a warning, and
it is the folder that says a draft with nothing answering it is still exported.
`solutions_in_a_second_source` is the other half of that sheet, and the only folder with two
documents in it: the questions in `source.md` and the worked solutions in `solutions.md`, which
the spec pairs onto them the way `in2lambda convert -a` pairs an answers file, so every solution
field is quoted from source 2 while the questions are quoted from source 1 - lines 5 and 7 of
each, which is why the fields say which source they came from. The note at the end of the
solutions is what the spec makes nothing of, and `mark ignore 2/b7` is a block of the second
source named as one.
`degrees` writes `^\circ` into the maths of both a question and the one worked solution answering
its two parts, and is the one folder whose report comes from `in2lambda.validation` over the set
the draft describes rather than from the checks over the draft itself: the solution is reported
against `q1.solution` rather than the parts it answers, since that is the field a `field replace`
would have to change, and reported once rather than once per part it was copied into.
