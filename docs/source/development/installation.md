# Installation

Fork the [GitHub project](https://github.com/lambda-feedback/content-conversion) to your account. Then, run the following with your GitHub handle in place of INSERT_GITHUB_NAME:

```shell
$ git clone https://github.com/INSERT_GITHUB_NAME/content-conversion
$ cd content-conversion
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
