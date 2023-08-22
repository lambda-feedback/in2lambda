# High Level Overview

% Credit for file structure: https://stackoverflow.com/a/38819161

% TODO: Find a way to auto-generate this?

```
tex2lambda
└── tex2lambda
    ├── api
    │   ├── module
    │   ├── part
    │   └── question
    ├── filters
    ├── json_convert
    ├── main.py
    └── katex_convert
```

tex2lambda follows the following workflow:

```
Question/Answer File ─filters+api─> Python Object ─json_convert─> Lambda Feedback JSON
```

A [pandoc filter](https://pandoc.org/filters.html) is written using [panflute](https://github.com/sergiocorreia/panflute) to parse different file structures. For instance, maybe questions are denoted using lists, or the answers directly follow the question.

Whilst running the filter, python functions which are part of the tex2lambda API help denote where text extracted from the file should go in a Lambda Feedback question. This is represented internally as separate objects for each part, question and module.

Finally, `json_convert` takes the questions in a python module object and converts it into zip files that can be imported through Lambda Feedback.
