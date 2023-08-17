# Documentation

The documentation can be found in `docs/source` and can be written in Markdown or reStructuredText. The library reference is written as docstrings in the source code itself.

`docs/index.md` defines the documentation structure.

To build the documentation, run the following from the root directory:

```shell
$ sphinx-build -v docs/source docs/_build/html
```

Use a browser to open the html files in `docs/_build/html/`.
