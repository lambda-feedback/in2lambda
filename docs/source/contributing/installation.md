# Installation

:::{important}
The standard installation method can be found in the [Quickstart](../quickstart). These instructions are for development purposes.
:::

Fork the [GitHub project](https://github.com/lambda-feedback/tex2lambda) to your account. Then, run the following with your GitHub handle in place of GITHUB_NAME:

```shell
$ git clone https://github.com/GITHUB_NAME/tex2lambda
$ cd tex2lambda
```

The project can then be installed such that any local changes are applied automatically.

## Poetry


Install [poetry](https://python-poetry.org/) and then run the following:

```shell
$ poetry install
$ poetry shell
$ tex2lambda --help
```

## pip

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tex2lambda?style=flat-square&logo=python&logoColor=white)](https://pypi.org/project/tex2lambda/)

:::{warning}
This method only installs the necessary dependencies to run `tex2lambda`, without any developer/documentation libraries.
:::


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
