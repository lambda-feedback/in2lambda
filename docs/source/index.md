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
Automagically uploads questions to [Lambda Feedback](https://lambda-feedback.github.io/user-documentation/) so you don't have to.

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
Can be used to process numerous file formats with a variety of different structures by using [pandoc filters](https://pandoc.org/filters.html).
:::

:::{grid-item-card} {octicon}`terminal;1.5em` Accessible Command Line Tool
:link: reference/command-line
:link-type: doc
Just provide the question file and select one of the in-built file parsers.
:::

:::{grid-item-card} {octicon}`gear;1.5em` Powerful API
:link: reference/library
:link-type: doc
A fully type-annotated extensively documented Python library is available for those that need a bit more control.
:::

::::

```{toctree}
:hidden:

🔎 Overview <self>
quickstart
filters/index
```

```{toctree}
:caption: 🔨 Contributing
:hidden:

contributing/installation
contributing/high_level
contributing/documentation
```

```{toctree}
:caption: 📖 Reference
:hidden:
:glob:

reference/*
```
