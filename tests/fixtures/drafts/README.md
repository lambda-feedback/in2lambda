# Drafts built by commands

Each folder here is one run: a `source.md` to freeze, the `commands.json` to apply to the draft
of it, and the `expected.json` those commands should leave in the draft's `fields`. The test
freezes the source, applies each command, compares the fields, and then replays the draft from
its log and checks the file is unchanged byte for byte - so a folder covers both what a command
writes and that it can be rebuilt from what it recorded.

To cover another command, add a folder. `mark_ignore` is the `sources/markdown` document with two
of its blocks marked as nothing to take a question from. `two_questions` is a sheet with a title, a
rubric, two questions with a part each and a separate solutions section, written out by every
command there is: the second question runs into its part with no blank line between them, so the
parser makes one block of the two and `split block` cuts it, and the first question's part is typed
out rather than quoted, because the source writes it with an `(a)` the field should not carry.
`field_replace` is a sheet the OCR left a brace out of the maths of: one `field replace` puts the
brace back and another, with `--regex`, collapses a doubled space in the solution, so both fields
end up edited while their ranges still name the lines they were quoted from.
