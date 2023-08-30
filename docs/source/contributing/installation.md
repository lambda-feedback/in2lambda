# Development Setup

:::{important}
The standard installation method can be found in the [Quickstart](../quickstart). These instructions are for development purposes.
:::

Fork the [GitHub project](https://github.com/lambda-feedback/tex2lambda) to your account. Then, run the following with your GitHub handle in place of GITHUB_NAME:

```shell
$ git clone https://github.com/GITHUB_NAME/tex2lambda
$ cd tex2lambda
```

The project can then be installed using [poetry](https://python-poetry.org/):

```shell
$ poetry install
$ poetry shell
$ pre-commit install
$ tex2lambda --help
```

:::{admonition} Using pip
:class: dropdown

Using pip alone is not recommended since it only installs the necessary dependencies to run `tex2lambda`, without any developer/documentation libraries. However, it could be useful for testing small modifications.

First, we create and activate a [virtual environment](https://docs.python.org/3/library/venv.html):

```shell
$ python -m venv env
$ source env/bin/activate
```

Then install in [editable mode](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs):

```shell
$ pip install -e .
$ tex2lambda --help
```
:::
