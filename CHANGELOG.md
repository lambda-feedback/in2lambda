# Changelog

## 2.0.0

- Converting a document is now `in2lambda convert FILE FILTER`, with the same options as before (`-o/--out`, `-a/--answers`). Scripts and Docker invocations that run `in2lambda FILE FILTER` need the extra word.
- `in2lambda FILE FILTER` exits with an error naming the command to run instead, rather than printing its usage and exiting successfully.
- beartype is now `^0.22`. At 0.20.0 and below its import hook leaves `cli` a plain function rather than a group, so the new command line either fails to import or runs `convert` whatever the arguments; 0.20.1 is the first version that works.
- `in2lambda source add FILE` freezes a document: it converts .docx and .tex to markdown beside the file, and writes a `draft.json` holding the markdown's hash and every block in it with the lines it spans, so that another tool can quote the source by line range. `in2lambda source show` prints that markdown numbered with the block ids. Freezing a file that has changed since is refused unless `--start-over` says to discard the draft, and so is showing one, since its block ids would name lines they are not the ids of. Both need pandoc and the `convert` extra, as `convert` does.
- The Python API is unchanged: `in2lambda.main.runner` and everything under `in2lambda.api` take the same arguments and return the same objects.
