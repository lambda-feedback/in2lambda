# -*- coding: utf-8 -*-
"""
Created on Wed Jul  5 19:13:28 2023

@author: Matthew Howarth
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
    # Replace incompatible LaTeX functions with KaTeX compatible equivalents
    katex_string = replace_functions(delete_functions(latex_string))
    return katex_string


def delete_functions(latex_string: str) -> str:
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
                    item=item+"(?![a-zA-Z])"

    return latex_string


def replace_functions(latex_string: str) -> str:
    replacement_dict = {}  # Dictionary to store the formatted values

    with open(Path(__file__).with_name("replace_list.txt"), "r") as file:
        for line in file:
            # Removing leading/trailing whitespaces, newlines, and commas
            line = line.strip().replace(",", "")
            # Splitting the line into key and value based on the colon
            key, value = line.split(":", 1)
            # Removing leading/trailing whitespaces from the key and value
            key = key.strip()
            value = value.strip()
            # Adding the formatted key-value pair to the dictionary

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
    latex_input = "B"
    katex_output = latex_to_katex(latex_input)
    print(katex_output)
