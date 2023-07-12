# -*- coding: utf-8 -*-
"""
Created on Wed Jul  5 19:13:28 2023

@author: Matthew Howarth
"""
import re


def latex_to_katex(latex_string: str) -> str:
    # Replace incompatible LaTeX functions with KaTeX compatible equivalents
    katex_string = replace_functions(delete_functions(latex_string))
    return katex_string


def delete_functions(latex_string: str) -> str:
    file_path = "tex2lambda/katex_convert/delete_list.txt"
    delete_list = []

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line:  
                raw_line = r"{}".format(line)
                delete_list.append(raw_line)
    for item in delete_list:
        while re.search(item, latex_string):
            match=re.search(item, latex_string)
            if match:
                start_index=match.start()
                end_index=match.end()
                if latex_string[end_index]=="{":
                    latex_string = brace_remover(latex_string, end_index)
                latex_string = latex_string[:start_index-1] + latex_string[end_index:]


    return latex_string

def replace_functions(latex_string: str) -> str:
    file_path = "tex2lambda/katex_convert/replace_list.txt"  # Replace with your file path

    replacement_dict = {}  # Dictionary to store the formatted values

    with open(file_path, "r") as file:
        for line in file:
            # Removing leading/trailing whitespaces, newlines, and commas
            line = line.strip().replace(",", "")
            # Splitting the line into key and value based on the colon
            key, value = line.split(":", 1)
            # Removing leading/trailing whitespaces from the key and value
            key = key.strip()
            value = value.strip()
            # Adding the formatted key-value pair to the dictionary
            replacement_dict[key] = value

    # replace the incompatible functions with their KaTeX equivalents using re.sub
    for old, new in replacement_dict.items():
        latex_string = re.sub(old, new, latex_string)
    return latex_string

def brace_remover(latex_string, brace_start_index):
    index_count = brace_start_index+1
    level_count = 0

    while level_count >= 0:
        index_count += 1
        match latex_string[index_count]:
            case "{":
                level_count += 1
            case "}":
                level_count -= 1

    latex_string = latex_string[:brace_start_index] + latex_string[brace_start_index+1:]
    latex_string = latex_string[:index_count-1] + latex_string[index_count:]
    return latex_string

    

if __name__ == "__main__":
    latex_input = r"""

"""

    katex_output = latex_to_katex(latex_input)
    print(katex_output)
