"""Functions relating to converting LaTeX expressions into valid KaTeX.

Due to custom macros/third-party libraries/etc. it can never be guaranteed to work. It works best
with simpler cases.
"""

import logging
import re
from pathlib import Path

# Create a logger object with a name and a level
logger = logging.getLogger("log")
logger.setLevel(logging.INFO)

# Create a file handler to write the messages to a file
file_handler = logging.FileHandler("log", mode="w")  # Clears log with every run
file_handler.setLevel(logging.INFO)

# Create a formatter to format the messages
formatter = logging.Formatter("%(message)s")

# Add the formatter to the file handler
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)


def latex_to_katex(latex_string: str) -> str:
    """Replace incompatible LaTeX functions with KaTeX compatible equivalents.

    Args:
        latex_string: A LaTeX string to be converted into valid KaTeX.

    Returns:
        Hopefully, a valid KaTeX expression that's similar to the LaTeX expression.

    Examples:
        >>>
    """
    katex_string = replace_functions(delete_functions(latex_string))
    return katex_string


def delete_functions(latex_string: str) -> str:
    """Helper method of `latex_to_katex` that deletes any LaTeX expressions with no KaTeX equivalent.

    Args:
        latex_string: A LaTeX string to be converted into valid KaTeX.

    Returns:
        The same LaTeX string with some commands removed.
    """
    delete_list = []

    with open(Path(__file__).with_name("delete_list.txt"), "r") as file:
        for line in file:
            line = line.strip()
            if line:
                delete_list.append(line)

    for item in delete_list:
        while re.search(item, latex_string):
            match = re.search(item, latex_string)
            if match:
                start_index = match.start()
                end_index = match.end()
                if not latex_string[end_index].isalpha():
                    logger.info(f"Deleted {latex_string[start_index:end_index]}")

                    if latex_string[end_index] == "{":
                        latex_string = brace_remover(latex_string, end_index)
                    latex_string = latex_string[:start_index] + latex_string[end_index:]
                else:
                    item = item + "(?![a-zA-Z])"

    return latex_string


def replace_functions(latex_string: str) -> str:
    """Helper method of `latex_to_katex` that replaces some LaTeX expressions with an equivalent KaTeX one.

    Args:
        latex_string: A LaTeX string to be converted into valid KaTeX.

    Returns:
        The same LaTeX string with some commands replaced where necessary.
    """
    replacement_dict = {}  # Dictionary to store the formatted values

    with open(Path(__file__).with_name("replace_list.txt"), "r") as file:
        for line in file:
            line = line.strip().replace(",", "")
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            pattern = re.compile(key)
            match = pattern.search(value)

            if match:
                key = key + "(?![a-zA-Z])"

            replacement_dict[key] = value

    logger.info("")

    # replace the incompatible functions with their KaTeX equivalents using re.sub
    for old, new in replacement_dict.items():
        while re.search(old, latex_string):
            match = re.search(old, latex_string)
            if match:
                logger.info(f"Replaced {old} with {new}")
                latex_string = re.sub(old, new, latex_string)
    return latex_string


def brace_remover(latex_string: str, brace_start_index: int) -> str:
    """Used to remove the arguments + braces of a given LaTeX command.

    This is used as part of `delete_functions` to remove any deleted functions arguments.

    Args:
        latex_string: A LaTeX string to be converted into KaTeX.
        brace_start_index: The indes of the start brace following a command.

    Returns:
        The same string but with the brace at the start index, any arguments and the end brace removed.
    """
    index_count = brace_start_index + 1
    level_count = 0

    while level_count >= 0:
        index_count += 1
        match latex_string[index_count]:
            case "{":
                level_count += 1
            case "}":
                level_count -= 1

    latex_string = (
        latex_string[:brace_start_index] + latex_string[brace_start_index + 1 :]
    )
    latex_string = latex_string[: index_count - 1] + latex_string[index_count:]
    return latex_string


if __name__ == "__main__":
    latex_input = "\\textbf{Vector Algebra:} for two vectors $\\vec{a}$ and $\\vec{b}$ in $\\mathbb{R}^3$ given by \\norm{a}"

    katex_output = latex_to_katex(latex_input)
    print(katex_output)
