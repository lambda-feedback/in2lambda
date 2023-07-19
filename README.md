# content-conversion
A Python library and CLT for converting LaTeX documents into Lambda Feedback format.

## Installation

First, ensure that [pandoc](https://pandoc.org/) is installed. 

### PyPi

```
$ pip install https://github.com/lambda-feedback/content-conversion/archive/main.zip
$ tex2lambda --help
```

It can also be installed via [pipx](https://pypa.github.io/pipx/).

## Usage

<!--- TODO: Automate this help output. -->

```
$ tex2lambda --help

 Usage: tex2lambda [OPTIONS] TEX_FILE {Materials}

 Takes in a TEX_FILE for a given SUBJECT and produces Lambda Feedback
 compatible json/zip files.

╭─ Options ─────────────────────────────────────────────────────────────────╮
│ --out   -o  PATH  Directory to output json/zip files to. [default: ./out] │
│ --help            Show this message and exit.                             │
╰───────────────────────────────────────────────────────────────────────────╯

 See the docs at https://lambda-feedback.github.io/user-documentation/ for
 more details.
```

For instance, the following takes in a Materials question sheet and produces JSON/ZIP files to `./out`:

```
$ tex2lambda problemsA_v2.7.tex Materials
```

Warnings will be generated if the image directory isn't in the correct location relative to the LaTeX file.

## Local Development

You can obtain the development version by cloning the repository:

```
$ git clone https://github.com/lambda-feedback/content-conversion
$ cd content-conversion
```

The project can then be installed such that any local changes are applied automatically.

### Poetry

Install [poetry](https://python-poetry.org/) and then run the following:

```
$ poetry install
$ poetry shell
$ tex2lambda --help
```

### pip

First, we create and activate a [virtual environment](https://docs.python.org/3/library/venv.html):

```
$ python -m venv env
$ source env/bin/activate
```

Then we install in [editable mode](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs):

```
$ pip install -e .
$ tex2lambda --help
```
