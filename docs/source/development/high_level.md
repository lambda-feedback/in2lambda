# High Level Overview

% Credit for file structure: https://stackoverflow.com/a/38819161

```
content-conversion
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
LaTeX ──filters+api──> Python Object ──json_convert──> Lambda Feedback JSON
```

A [pandoc filter](https://pandoc.org/filters.html) is written using [panflute](https://github.com/sergiocorreia/panflute) to parse different file structures. For instance, maybe questions are denoted using lists, or the answers directly follow the question.

Then, the python functions that are part of the tex2lambda API help denote where where text extracted from the file should go in a Lambda Feedback question. This is represented internally via classes (a class for a part, question and module).

Finally, {code}`json_convert` takes the questions in a python module object and converts it into zip files that can be imported through Lambda Feedback.
