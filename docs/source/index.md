---
og:title: in2lambda
---

::::{grid} 1 2 2 2
:padding: 0

:::{grid-item}
:child-align: center
<div align="center">
    <h1>in2lambda</h1>
    <a href="https://pypi.org/project/in2lambda/">
        <img alt="PyPI - Version" src="https://img.shields.io/pypi/v/in2lambda?style=flat-square&logo=pypi&logoColor=white&color=blue">
    </a>
    <a href="https://app.codecov.io/github/lambda-feedback/in2lambda">
        <img alt="Codecov" src="https://img.shields.io/codecov/c/github/lambda-feedback/in2lambda?style=flat-square&logo=codecov">
    </a>
</div>
:::

:::{grid-item}
\
\
Converts a document of questions into a question set that [Lambda Feedback](https://lambda-feedback.github.io/user-documentation/) imports.

```{button-ref} quickstart
:ref-type: doc
:color: primary
:expand:

Get Started
```
:::

::::

::::{grid} 1 3 3 3

:::{grid-item-card} {octicon}`tools;1.5em` Highly Configurable
:link: filters/index
:link-type: doc
Reads many file formats, and documents of many structures, through [pandoc filters](https://pandoc.org/filters.html).
:::

:::{grid-item-card} {octicon}`terminal;1.5em` Accessible Command Line Tool
:link: reference/command-line
:link-type: doc
Name the question file and one of the built-in filters.
:::

:::{grid-item-card} {octicon}`gear;1.5em` Powerful API
:link: reference/library
:link-type: doc
A type-annotated, documented Python library builds a question set without a source document.
:::

::::

```{toctree}
:hidden:

🔎 Overview <self>
quickstart
question-format
filters/index
spec
```

```{toctree}
:caption: 🔨 Contributing
:hidden:

contributing/installation
contributing/high_level
contributing/documentation
contributing/new_version
```

```{toctree}
:caption: 📖 Reference
:hidden:
:glob:

reference/*
```
