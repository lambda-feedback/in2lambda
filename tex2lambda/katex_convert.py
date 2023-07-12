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
    delete_list = tuple(
        [
            r"\\usepackage\\{.*?}",
            r"\\lhead\\{.*?}",
            r"\\pagestyle\\{.*?}",
            r"\\setcounter\\{.*?}+{.*?}",
            r"\\documentclass\\[.*?]+{.*?}",
            r"\\label{.*?}",
            r"\\ref",
            r"\\eqref",
            r"\\caption{.*?}",
            r"\\begin{figure}",
            r"\\begin{document}",
            r"\\end{document}",
            r"\\end{figure}",
            r"\\begin{center}",
            r"\\end{center}",
            r"\\begin{enumerate}",
            r"\\end{enumerate}",
            r"\\item",
            r"\\begin{problem}",
            r"\\end{problem}",
            r"\\begin{tabular}",
            r"\\end{tabular}",
            r"\\begin{flushright}+(.*?)",
            r"\\end{flushright}+(.*?)",
            r"\\centerline",
            r"\\bigskip",
            r"\\medskip",
            r"\\smallskip",
            r"\\noindent",
            r"\\vrulefill",
            r"\\vfill",
            r"\\vfil",
            r"\\hrulefill",
            r"\\hfill",
            r"\\hfil",
            r"\\hline",
            r"\\vline",
            r"\\setlength{.*?}",
            r"\[h(!)?\\]",
            r"\[ht(!)?\\]",
            r"\[t(!)?\\]",
            r"\[b(!)?\\]",
            r"\[p(!)?\\]",
            r"\[!\\]",
            r"\[H(!)?\\]",
            r"{l+\\}",
            r"{}",
            r"\\abovewithdelims",
            r"\\atopwithdelims",
            r"\\overwithdelims",
            r"\\and",
            r"\\array",
            r"\\bbox",
            r"\\bigominus",
            r"\\bigoslash",
            r"\\bigsqcap",
            r"\\bracevert",
            r"\\buildrel",
            r"\\C",
            r"\\cancelto",
            r"\\cases",
            r"\\cee",
            r"\\cf",
            r"\\class",
            r"\\cline",
            r"\\Coppa",
            r"\\coppa",
            r"\\cssld",
            r"\\dddot",
            r"\\ddddot",
            r"\\DeclareMathOperator(\\*)?\\{.*?}+{.*?}",
            r"\\definecolor(\\*)?\\{.*?}+{.*?}+{.*?}",
            r"\\Digamma",
            r"\\else",
            r"\\enclose\\{.*?}+\\[.*?]+{.*?}",
            r"\\idotint",
            r"\\iddots",
            r"\\if",
            r"\\fi",
            r"\\ifmode",
            r"\\ifx",
            r"\\iiiint",
            r"\\itshape",
            r"\\Koppa",
            r"\\koppa",
            r"\\leftroot",
            r"\\leqalignno",
            r"\\lower",
            r"\\mathtip",
            r"\\mbox",
            r"\\md",
            r"\\mdseries",
            r"\\mmltoken",
            r"\\moveleft",
            r"\\moveright",
            r"\\mspace",
            r"\\multicolumn(\\*)?\\{.*?}+{.*?}+{.*?}",
            r"multiline}",
            r"\\Newextarrow",
            r"\\newcounter\\{.*?}",
            r"\\newenvironment\\{.*?}?+\\[.*?]+{.*?}+{.*?}",
            r"\\addtocounter\\{.*?}+{.*?}",
            r"\\normalfont",
            r"\\oldstyle",
            r"\\or",
            r"\\pagecolor",
            r"\\part",
            r"\\Q",
            r"\\newtheorem\\{.*?}+{.*?}",
            r"\\raise",
            r"\\raisebox",
            r"\\require\\{.*?}",
            r"\\root",
            r"\\newtheorem\\{\\}",
            r"\\Sampi",
            r"\\sampi",
            r"\\sc",
            r"\\scalebox\\{.*?}",
            r"\\setlength\\{.*?}+{.*?}",
            r"\\shoveleft",
            r"\\shoveright",
            r"\\sideset\\{.*?}+{.*?}",
            r"\\SI",
            r"\\unit",
            r"\\skew",
            r"\\skip",
            r"\\sl",
            r"\\smiley",
            r"\\Stigma",
            r"\\stigma",
            r"\\strut",
            r"\\style",
            r"{subarray}",
            r"\\textsl",
            r"\\texttip",
            r"\\textvisiblespace",
            r"\\toggle",
            r"\\unicode",
            r"\\up",
            r"\\uproot",
            r"\\upshape",
            r"\\varcoppa",
            r"\\varstigma",
            r"\\wideparen",
        ]
    )

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
    # dictionary of LaTeX functions to replace
    replacements = {
        r"\\begin{eqnarray}": r"\\begin{align}",
        r"\\end{eqnarray}": r"\\end{align}",
        r"\\begin{eqnarray\\*}": r"\\begin{align*}",
        r"\\end{eqnarray\\*}": r"\\end{align*}",
        r"\\begin{eqalign}": r"\\begin{align}",
        r"\\end{eqalign}": r"\\end{align}",
        r"\\begin{align\\*}": r"\\begin{align*}",
        r"\\end{eqalign\\*}": r"\\end{align*}",
        r"\\ang": r"\\angle",
        r"\\Arrowvert": r"\\Vert",
        r"\\arrowvert": r"\\vert",
        r"\\bfseries": r"\\textbf",
        r"\\emph": r"\\textit",
        r"\\euro": r"",
        r"\\LeftArrow": r"\\leftarrow",
        r"\\mit": r"\\mathit",
        r"\\overbracket": r"\\overbrace",
        r"\\rule": r"\\Rule",
        r"\\overparen": r"\\overgroup",
        r"\\scr": r"\\mathscr",
        r"\\Space": r"\\space",
        r"\\Tiny": r"\\tiny",
        r"\\underparen": r"\\undergroup",
        r"\\underbracket": r"\\underbrace",
    }

    # replace the incompatible functions with their KaTeX equivalents using re.sub
    for old, new in replacements.items():
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
    latex_input = r"""\begin{eqnarray}
$x^2+x+2=0$
\raise{test}
\raise{test}

"""

    katex_output = latex_to_katex(latex_input)
    print(katex_output)
