"""Python library and CLT for converting LaTeX documents into Lambda Feedback compatible JSON/ZIP files."""

import click
import panflute
import rich_click
from beartype.claw import beartype_this_package
from rich.traceback import install

beartype_this_package()
# TODO: Automate suppresion list for third party modules
# See: https://rich.readthedocs.io/en/stable/traceback.html#suppressing-frames
install(show_locals=True, suppress=[panflute, click, rich_click])
