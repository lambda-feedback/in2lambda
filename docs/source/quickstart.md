# 🚀 Quickstart

This page describes how to install in2lambda and convert a document into a Lambda Feedback question set.

## 1. Installation

### Docker

[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/lambda-feedback/in2lambda/docker-publish.yml?style=flat-square&logo=docker&label=Docker)](https://github.com/lambda-feedback/in2lambda/pkgs/container/in2lambda)

The following command starts an interactive container holding in2lambda, with the current working directory mounted at `/files`:

```bash
$ docker run -it --rm -v $(pwd):/files ghcr.io/lambda-feedback/in2lambda sh
```

Run in2lambda over those files inside the container.

```bash
$ cd files
$ in2lambda --help
$ ...
$ exit
```

Docker stops and deletes the container on exit. The image stays on disk for the next run.

### PyPi

[![PyPI - Version](https://img.shields.io/pypi/v/in2lambda?logo=pypi&logoColor=white&color=blue&style=flat-square)](https://pypi.org/project/in2lambda/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/in2lambda?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/in2lambda/)


[pip](https://pip.pypa.io/en/stable/) installs in2lambda. To write questions in Python:

```shell
$ pip install in2lambda
```

To convert documents, install the `convert` extra and [pandoc](https://pandoc.org/installing.html):

```shell
$ pip install 'in2lambda[convert]'
$ in2lambda --help
```

[pipx](https://pypa.github.io/pipx/) installs in2lambda as well.

## 2. Choose a Document

`in2lambda convert` takes two arguments:

- The path to a document.
- A filter describing how to parse that document.

The [filters page](filters/index) lists every filter.

The following command reads `questions.tex` with a filter that expects [each part to be followed by its solution](filters/_autosummary/PartSolPartSol):

```bash
$ in2lambda convert questions.tex PartSolPartSol
```

:::{note}
The filter name is case-insensitive.
:::

A different filter reads [answers held in a separate file](filters/_autosummary/PartsSepSol):

```bash
$ in2lambda convert questions.tex -a solutions.tex PartsSepSol
```

`in2lambda convert` writes an `out` directory in the directory the command ran in, holding the zipped question files.

Before writing that directory, in2lambda prints the problems that would stop Lambda Feedback importing the set or would render it wrongly: an answer that does not fit the box marking it, a figure the export would not contain, maths KaTeX cannot display. Each problem names the question, the part and the field holding it. Each problem is a warning, and in2lambda writes the `out` directory whatever it finds, because an author may have intended the problem.

in2lambda checks the maths by rendering it with KaTeX, as Lambda Feedback renders it, which needs [Node.js](https://nodejs.org). Without Node.js, in2lambda runs the other checks and reports that it did not check the maths.

With [xelatex](https://tug.org/texlive/) installed alongside pandoc, in2lambda also compiles the set as Lambda Feedback compiles a PDF of it, and names the field holding each LaTeX error. Without xelatex, in2lambda prints one warning naming the packages to install.

The [command line reference](reference/command-line) describes every command and option.

## 3. Import into Lambda Feedback

Open a set in teacher mode. The arrow beside the "Add Question" button imports a question from a file.

Choose the zip file to upload, and Lambda Feedback adds the question to the set.

An imported question arrives published, with every display setting on, and the set's own visibility settings apply to it. The Python API sets each of these per question; see the
[question format](question-format).

![Importing Question from file in Teacher Mode](_static/images/import-teacher.png)
