# Drafts built by commands

Each folder here is one run: a `source.md` to freeze, the `commands.json` to apply to the draft
of it, the `expected.json` those commands should leave in the draft's `fields`, and the
`report.json` that `in2lambda validate` should then find in it - a folder with no `report.json`
is a draft with nothing wrong with it. The test freezes the source, applies each command, checks
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
commands can make one.
