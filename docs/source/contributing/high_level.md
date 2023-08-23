# High Level Overview

```{eval-rst}
.. graphviz::
    :caption: tex2lambda Workflow Overview
    :alt: tex2lambda Workflow Overview Diagram

    digraph tex2lambda_workflow {
        rankdir="LR";

        subgraph cluster_tex2lambda {
            color=blue;
            label=<<b>tex2lambda</b>>;
            
            filters [label="Pandoc Filter", fillcolor="#F0F0F0"];
            python_object [label=<<table border='0' cellborder='1' cellspacing='0' cellpadding='5'>
                <tr><td colspan="3" bgcolor="#D0D0D0"><b>Python Object</b></td></tr>
                <tr>
                    <td port='port_one'><i>Module</i></td>
                    <td port='port_two'><i>Question</i></td>
                    <td port='port_three'><i>Part</i></td>
                </tr>
            </table>>, shape=none];
        }

        node [style="filled", fillcolor="#F0F0F0"];
        question_file [label="Question File", shape="note"];
        answer_file [label="Answer File", shape="note"];
        json [label="JSON/ZIP files", shape="folder"];
        lambda_feedback [label="Lambda Feedback", shape="component"];

        question_file -> filters [label="CLT"];
        answer_file -> filters [label="CLT", style=dashed];
        filters -> python_object [label="API"];
        python_object -> json [label="json_convert"];
        json -> lambda_feedback [label="browser"];
    }
```

A [pandoc filter](https://pandoc.org/filters.html) is written using [panflute](https://github.com/sergiocorreia/panflute) to parse different file structures. For instance, maybe questions are denoted using lists, or the answers directly follow the question.

Whilst running the filter, python functions which are part of the tex2lambda API help denote where text extracted from the file should go in a Lambda Feedback question. This is represented internally as separate objects for each part, question and module.

Finally, `json_convert` takes the questions in a python module object and converts it into zip files that can be imported through Lambda Feedback.
