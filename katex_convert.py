# -*- coding: utf-8 -*-
"""
Created on Wed Jul  5 19:13:28 2023

@author: Matthew Howarth
"""
import re

def latex_to_katex(latex_string):
    # Replace incompatible LaTeX functions with KaTeX compatible equivalents
    katex_string = replace_incompatible_functions(latex_string)

    return katex_string

def replace_incompatible_functions(latex_string):
    #dictionary of LaTeX functions to replace
    replacements = {
        r'\\begin{eqnarray}': r'\\begin{align*}',
        r'\\end{eqnarray}': r'\\end{align*}',
        r'\\nonumber': r''
    }

    #replace the incompatible functions with their KaTeX equivalents using re.sub
    for old, new in replacements.items():
        latex_string = re.sub(old, new, latex_string)

    return latex_string

latex_input = r'''
\begin{eqnarray}
    f(x) &= x^2 + 2x + 1 \nonumber \\
    g(x) &= \frac{\sin(x)}{\cos(x)} \nonumber
\end{eqnarray}
'''

print(latex_input)
katex_output = latex_to_katex(latex_input)
print(katex_output)