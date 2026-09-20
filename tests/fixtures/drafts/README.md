# Drafts built by commands

Each folder here is one run: a `source.md` to freeze, the `commands.json` to apply to the draft
of it, and the `expected.json` those commands should leave in the draft's `fields`. The test
freezes the source, applies each command, compares the fields, and then replays the draft from
its log and checks the file is unchanged byte for byte - so a folder covers both what a command
writes and that it can be rebuilt from what it recorded.

To cover another command, add a folder. `mark_ignore` is the `sources/markdown` document with two
of its blocks marked as nothing to take a question from.
