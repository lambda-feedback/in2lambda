# High Level Overview

```{eval-rst}
.. graphviz:: ../diagrams/workflow.dot
    :alt: tex2lambda Workflow Overview Diagram
    :align: right
```

A [pandoc filter](https://pandoc.org/filters.html) is written using [panflute](https://github.com/sergiocorreia/panflute) to parse different file structures. For instance, maybe questions are denoted using lists, or the answers directly follow the question.

Whilst running the filter, python functions which are part of the tex2lambda API help denote where text extracted from the file should go in a Lambda Feedback question. This is represented internally as separate objects for each part, question and module.

Finally, `json_convert` takes the questions in a python module object and converts it into zip files that can be imported through Lambda Feedback.
