# Changelog

## 2.0.0

- Converting a document is now `in2lambda convert FILE FILTER`, with the same options as before (`-o/--out`, `-a/--answers`). Scripts and Docker invocations that run `in2lambda FILE FILTER` need the extra word.
- `in2lambda FILE FILTER` exits with an error naming the command to run instead, rather than printing its usage and exiting successfully.
- beartype is now `^0.22`. At 0.20.0 and below its import hook leaves `cli` a plain function rather than a group, so the new command line either fails to import or runs `convert` whatever the arguments; 0.20.1 is the first version that works.
- The Python API is unchanged: `in2lambda.main.runner` and everything under `in2lambda.api` take the same arguments and return the same objects.
