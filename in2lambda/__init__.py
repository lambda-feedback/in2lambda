"""Python library and CLT for converting LaTeX documents into Lambda Feedback compatible JSON/ZIP files."""

import beartype
import click
import rich_click
from beartype.claw import beartype_this_package
from rich.traceback import install

beartype_this_package()
# TODO: Automate suppresion list for third party modules
# See: https://rich.readthedocs.io/en/stable/traceback.html#suppressing-frames
_suppress = [click, rich_click, beartype]
try:  # panflute is only installed with the convert extra.
    import panflute

    _suppress.append(panflute)
except ImportError:
    pass
install(show_locals=True, suppress=_suppress)
