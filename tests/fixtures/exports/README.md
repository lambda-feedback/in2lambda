# Real Lambda Feedback exports

Each folder here is a question set exactly as Lambda Feedback exported it. Do not edit, reformat
or re-save these files: their value is that they are what the platform really produces. To add
coverage, add another export as a new folder.

## What an export contains

```
set_<Name>.json
question_000_<Title_with_underscores>.json     # 000 is the question's orderNumber
question_001_...
media/question_000_<Title>_0001.png            # referenced from the questions by basename
```

JSON files are written on a single line.

The keys of each file, and the Python attribute that fills each one, are described in
[`docs/source/question-format.md`](../../../docs/source/question-format.md).
