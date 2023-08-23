import importlib
import os
import shutil
import pkgutil
from pathlib import Path

import tex2lambda.filters


def generate_filters_docs():
    filters_directory = Path("./filters")
    """Top-level filters documentation folder."""
    autosummary_directory = filters_directory / "_autosummary"
    """Where the auto-generated rst files for the filters are stored."""
    static_pdf_directory = Path("./_static/pdf")
    """Where to store the PDFs of the minimal examples."""

    autosummary_directory.mkdir(exist_ok=True, parents=True)
    static_pdf_directory.mkdir(exist_ok=True)

    filters = (
        i.name
        for i in pkgutil.iter_modules(tex2lambda.filters.__path__)
        if i.name[0] != "_"
    )

    for filter_name in filters:
        filter_module = importlib.import_module(
            f"tex2lambda.filters.{filter_name}.filter"
        )

        relative_directory = f"../../../../tex2lambda/filters/{filter_name}"
        """Where to find the filter's directory relative to `autosummary_directory`.
        
        For some reason, literalinclude requires it to be relative.
        If absolute were needed: f"{os.path.dirname(filter_module.__file__)}/filename"
        """
        filter_file = f"{relative_directory}/filter.py"
        tex_file = f"{relative_directory}/example.tex"

        if shutil.which("pdflatex"):
            os.system(
                f"pdflatex -output-directory={static_pdf_directory} -jobname={filter_name} -interaction=nonstopmode {tex_file}"
            )

            if not os.path.exists(f"{static_pdf_directory}/{filter_name}.pdf"):
                raise RuntimeError("PDF output not found")

        rst_content = f"""\
{filter_name}
{'*' * len(filter_name)}

{filter_module.__doc__}

Minimal Example
----------------

A PDF which this filter parses correctly is shown below:

.. dropdown:: 📄 LaTeX Code

   .. literalinclude:: {tex_file}
      :language: LaTeX

:pdfembed:`src:../../../_static/pdf/{filter_name}.pdf, height:700, width:100%, align:middle`

.. dropdown:: 🐍 Python Filter

   .. literalinclude:: {filter_file}
      :language: Python
"""

        rst_file_path = autosummary_directory / f"{filter_name}.rst"
        with open(rst_file_path, "w") as rst_file:
            rst_file.write(rst_content)
