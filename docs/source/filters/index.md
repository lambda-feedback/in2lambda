# 📚 Filters

Behind the scenes, tex2lambda makes use of [pandoc filters](https://pandoc.org/filters.html) to parse the question files.

:::{admonition} Why not manually parse the questions?
:class: dropdown

Parsing LaTeX is inherently difficult. See [here](https://tex.stackexchange.com/a/4205) for a full explanation.

Some potential complications include custom libraries, macros that have different meanings depending on context and nested expressions.

Pandoc helps deal with this by quickly generating a standardised JSON format that abstracts away a lot of unnecessary details. This allows us to write simpler, Pythonic parsers for many different file formats.
:::

Different filters should be used depending on the structure of the question file. For instance, maybe the solutions come directly after a part, or maybe there aren't any answers provided at all!

Please see the specific pages on each filter for more information:

```{toctree}
:maxdepth: 1
:glob:

_autosummary/*
```
