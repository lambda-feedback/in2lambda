# 🚀 Quickstart

This page gives a quick overview of how to get started with in2lambda to quickly add documents to Lambda Feedback.

## 1. Installation

### Docker

[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/lambda-feedback/in2lambda/docker-publish.yml?style=flat-square&logo=docker&label=Docker)](https://github.com/lambda-feedback/in2lambda/pkgs/container/in2lambda)

The following creates an interactive container which includes in2lambda and mounts the current working directory into `/files`:

```bash
$ docker run -it --rm -v $(pwd):/files ghcr.io/lambda-feedback/in2lambda sh
```

Within the container, we can access the files and run in2lambda as normal.

```bash
$ cd files
$ in2lambda --help
$ ...
$ exit
```

The container is stopped and deleted after exiting, although the image remains downloaded for future use.

### PyPi

[![PyPI - Version](https://img.shields.io/pypi/v/in2lambda?logo=pypi&logoColor=white&color=blue&style=flat-square)](https://pypi.org/project/in2lambda/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/in2lambda?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/in2lambda/)


:::{important}
Ensure that [pandoc](https://pandoc.org/installing.html) is already installed.
:::

in2lambda can be installed via [pip](https://pip.pypa.io/en/stable/):

```shell
$ pip install in2lambda
$ in2lambda --help
```

This can also be done through [pipx](https://pypa.github.io/pipx/).

## 2. Choose a Document

in2lambda takes in two arguments:

- The path to a document.
- A filter describing how to parse it.

A list of available filters can be found [here](filters/index).

For instance, the following takes in `questions.tex` and uses a filter that expects [each part to be directly followed by the solution](filters/_autosummary/PartSolPartSol):

```bash
$ in2lambda questions.tex PartSolPartSol
```

:::{note}
The filter name is case-insensitive. Don't worry about the capital letters.
:::

Another filter might be used if [the answers are in a separate file](filters/_autosummary/PartsSepSol):

```bash
$ in2lambda questions.tex -a solutions.tex PartsSepSol
```

By default, this generates an `out` directory in the same place that the command was run in. It contains the zipped question files.

Check the [command line tool reference](reference/command-line) for more information.

## 3. Import into Lambda Feedback

Click on a set in teacher mode. The arrow next to the "Add Question" button allows you to import a question from a file.

Choose the zip file you wish to upload, and the question should appear! 🎉

![Importing Question from file in Teacher Mode](_static/images/import-teacher.png)
