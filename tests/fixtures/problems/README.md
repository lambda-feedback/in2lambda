# Exports with one problem each

Each folder here is a hand-written Lambda Feedback export exhibiting exactly one of the problems
`in2lambda.validation.validate` looks for, beside the `expected.txt` report it should produce:
one `str(Problem)` line per problem, which the test compares sorted.

They are written by hand rather than exported by the platform, because the platform does not
produce broken sets. Real exports live in `../exports`, and the same test suite checks that none
of them is reported as having a problem.

A folder whose report says `KaTeX rejects it` needs Node.js, which KaTeX is rendered with, and is
skipped without it.

To cover a new check, add a folder. The set's `description` says what the folder is for. A folder
is loaded by `Set.from_json`, the same loader real exports go through rather than a lenient copy,
so it must carry every key that loader reads — they are listed in `../exports/README.md`.
