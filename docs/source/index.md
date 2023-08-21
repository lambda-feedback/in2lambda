---
og:title: tex2lambda
---

::::{grid} 1 2 2 2

:::{grid-item}
:child-align: center
<div align="center">
    <h1>tex2lambda</h1>
</div>
:::

:::{grid-item}
:padding: 3
Automagically uploads questions to [Lambda Feedback](https://lambda-feedback.github.io/user-documentation/) so you don't have to.

```{button-ref} quickstart
:ref-type: doc
:color: primary

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
:caption: 🔨 Development
:hidden:

development/installation
development/high_level
development/documentation
```

```{toctree}
:caption: 📖 Reference
:hidden:

reference/command-line
reference/library
```
