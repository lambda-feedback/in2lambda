# -*- coding: utf-8 -*-
"""
Created on Wed Jul  5 19:13:28 2023

@author: Matthew Howarth
"""
import re


def latex_to_katex(latex_string: str) -> str:
    # Replace incompatible LaTeX functions with KaTeX compatible equivalents
    katex_string = replace_incompatible_functions(latex_string)

    return katex_string


def replace_incompatible_functions(latex_string: str) -> str:
    # dictionary of LaTeX functions to replace
    replacements = {
        # replace with nothing
        r"\\label{.*?}": r"",  # delete label and argument
        r"\\ref": r"",  # delete ref and argument
        r"\\eqref": r"",
        r"\\begin{figure}": r"",  # delete centerline and argument
        r"\\end{figure}": r"",  # delete centerline and argument
        r"\\begin{center}": r"",  # delete centerline and argument
        r"\\end{center}": r"",  # delete centerline and argument
        r"\\begin{enumerate}": r"",
        r"\\end{enumerate}": r"",
        r"\\item": r"",
        r"\\caption{.*?}": r"",  # delete caption and argument
        r"\\centerline": r"",  # delete centerline and argument
        r"\\bigskip": r"",
        r"\\medskip": r"",
        r"\\smallskip": r"",  # skipping functions are unsupported
        r"\\noindent": r"",
        r"\\vrulefill": r"",
        r"\\vfill": r"",
        r"\\vfil": r"",
        r"\\hrulefill": r"",
        r"\\hfill": r"",
        r"\\hfil": r"",
        r"\\hline": r"",
        r"\\vline": r"",
        r"\\setlength{.*?}": r"",
        r"\[h(!)?\]": r"", # remove alignments
        r"\[ht(!)?\]": r"",
        r"\[t(!)?\]": r"",
        r"\[b(!)?\]": r"",
        r"\[p(!)?\]": r"",
        r"\[!\]": r"",  
        r"\[H(!)?\]": r"",
        r"\{l+\}": r"",
        r"[+-]?(\d*\.)?\d+pt": "",  # Matches ints or decimals followed by pt
        # r'-[0-9]*in':'',
        # r'[0-9]*in':'',  NOTE: GETS RID OF ALL in
        r"\{}": "",  # removes lone {} brackets
        # replace with something
        r"\\begin{eqnarray}": r"\\begin{align}",  # KaTeX does not support eqn array: replace with align
        r"\\end{eqnarray}": r"\\end{align}",
        r"\\begin{eqnarray*}": r"\\begin{align*}",  # KaTeX does not support eqn array: replace with align
        r"\\end{eqnarray*}": r"\\end{align*}",
    }

    # replace the incompatible functions with their KaTeX equivalents using re.sub
    for old, new in replacements.items():
        latex_string = re.sub(old, new, latex_string)

    while latex_string.startswith("{") and latex_string.endswith("}"):
        latex_string = latex_string[1:-1]  # Remove the first and last characters

    return latex_string

    # Remove extra outer curly brackets if the first character is a curly bracket


if __name__ == "__main__":
    latex_input = r"""\documentclass[12pt]{article}

\input{../../Shared/header}

\pagestyle{empty}
\setlength{\textheight}{9.6in}  \setlength{\textwidth}{6.5in}
\setlength{\oddsidemargin}{-0.15in} \setlength{\evensidemargin}{0.2in}
\setlength{\topmargin}{-50pt}

\setlength{\arraycolsep}{2pt}
\setlength{\parskip}{0pt}
\setlength{\parindent}{0pt}

\begin{document}

\centerline{\Large Complex Numbers, Functions and Ordinary Differential Equations}
\bigskip\bigskip



\noindent
Solutions to Problem Sheet 1\hfill 2023

\vskip-9pt\hrulefill

%\subsubsection*{Homework}

\begin{enumerate}

\item For a complex number $a+i\,b$, in which $a$ and $b$ are real, the real and imaginary parts
are given by ${\rm Re}(a+i\,b)=a$ and ${\rm Im}(a+i\,b)=b$, respectively.  Thus,

$
\begin{array}[h!]{l}
{\rm (a)}\hskip5pt {\rm Re}(8+3\,i)=8\, ,\qquad{\rm Im}(8+3\,i)=3\, .\\
\noalign{\vskip12pt}
{\rm (b)}\hskip5pt {\rm Re}(4-15\,i)=4\, ,\qquad {\rm Im}(4-15\,i)=-15\, .\\
\noalign{\vskip12pt}
{\rm (c)}\hskip5pt {\rm Re}(\cos\theta-i\,\sin\theta)=\cos\theta\, ,\qquad {\rm
Im}(\cos\theta-i\,\sin\theta)=-\sin\theta\, .\\
\noalign{\vskip12pt}
{\rm (d)}\hskip5pt i^2=-1.\quad  {\rm Re}(i^2)=-1\, ,\qquad {\rm Im}(i^2)=0\, .\\
\noalign{\vskip12pt}
{\rm (e)}\hskip5pt i\,(2-5\,i)=5+2\,i.\qquad  {\rm Re}(5+2\,i)=5\, ,\qquad {\rm Im}(5+2\,i)=2\, .\\
\noalign{\vskip12pt}
{\rm (f)}\hskip5pt (1+2\,i)(2-3\,i)=2-3\,i+4\,i+6=8+i\, .\qquad {\rm Re}(8+i)=8\, ,\qquad {\rm
Im}(8+i)=1\, .
\end{array}
$

\item Applying the rules for the multiplication and division of
  complex numbers yields:

$
\begin{array}[h!]{lll}
{\rm (a)}\hskip5pt (5-i)(2+3\,i)=10+15\,i-2\,i+3=13+13\,i\, .\\
\noalign{\vskip12pt}
{\rm (b)}\hskip5pt (3-4\,i)(3+4\,i)=9+12\,i-12\,i+16=25\, .\\
\noalign{\vskip12pt}
{\rm (c)}\hskip5pt (1+2\,i)^2=(1+2\,i)(1+2\,i)=1+2\,i+2\,i-4=-3+4\,i\, .\\
\noalign{\vskip12pt}
{\rm (d)}\hskip5pt \displaystyle{{10\over4-2\,i}={10\over4-2\,i}\times{4+2\,i\over4+2\,i}=
{40+20\,i\over16+8\,i-8\,i+4}={40+20\,i\over20}=2+i\, .}\\
\noalign{\vskip12pt}
{\rm (e)}\hskip5pt \displaystyle{{3-i\over4+3\,i}={3-i\over4+3\,i}\times{4-3\,i\over4-3\,i}=
{12-9\,i-4\,i-3\over16-12\,i+12\,i+9}={9-13\,i\over25}={9\over25}-i\,{13\over25}\, .}\\
\noalign{\vskip12pt}
{\rm (f)}\hskip5pt \displaystyle{{1\over i}={1\over i}\times{-i\over-i}=-i\, .}
\end{array}
$

\item We have that $z=(5+7\,i)(5+b\,i)=25+5b\,i+35\,i-7b$.

$
\begin{array}[h!]{l}
{\rm (a)}\hskip5pt {\rm If}\ b\ {\rm and}\ z\ {\rm are\ both\ real},\ {\rm then\ the \ imaginary\
parts\ of\ both\ quantities\ vanish.}\ {\rm Thus,}\\
\noalign{\vskip12pt}
\hskip20pt {\rm Im}(z)=35+5b=0, {\rm so}\ b=-7.\\
\noalign{\vskip12pt}
{\rm (b)}\hskip5pt {\rm If}\ {\rm Im}(b)={4\over5},\ {\rm and}\ z\ {\rm is\ pure\ imaginary,}\
{\rm then\ the\ real\ part\ of}\ z\ {\rm vanishes\!:}\\
\noalign{\vskip12pt}
\hskip20pt{\rm Re}(z)=25+5\bigl[i\,{\rm Im}(b)\bigr]i-7\,{\rm Re}(b)=25-4-7\,{\rm Re}(b)=21-7\,{\rm
Re}(b)=0,\\
\noalign{\vskip12pt}
\hskip20pt{\rm so}\ {\rm Re}(b)=3.
\end{array}
$


\item The graphical representation of the complex number $z=x+i\,y$ is
  the point $(x,y)$ on a set of axes where the $x$-axis corresponds to
  the real part of the complex number and the $y$-axis the imaginary
  part. The required points are

  \begin{center}
    \includegraphics[width=8cm]{PS1-2}
  \end{center}

\item For a complex number $z=x+i\,y$, the polar form is $z=r\,e^{i\theta}$, where
\begin{equation*}
r=\sqrt{x^2+y^2}\, ,\qquad
\theta={\rm tan}^{-1}\biggl({y\over x}\biggr)\, .
\end{equation*}

$\begin{array}[h!]{l}
{\rm (a)}\hskip5pt z=i.\  {\rm We\ have\ that}\ x=0\ {\rm and}\ y=1,\ {\rm so}\ r=1,\ {\rm and}\
\theta={1\over2}\pi.\ {\rm Thus}\ i=e^{i\,\pi/2}.\\
\noalign{\vskip12pt}
{\rm (b)}\hskip5pt z=-i.\ {\rm We\ have\ that}\ x=0\ {\rm and}\ y=-1,\ {\rm so}\ r=1,\ {\rm and}\
\theta={3\over2}\pi.\ {\rm Thus}\ -i=e^{3i\,\pi/2}.\\
\noalign{\vskip12pt}
{\rm (c)}\hskip5pt z=1+i.\ {\rm We\ have\ that}\ x=1\ {\rm and}\ y=1,\ {\rm so}\ r=\sqrt{2},\ {\rm
and}\ \theta={1\over4}\pi.\\
\noalign{\vskip12pt}
\hskip20pt{\rm Thus}\ 1+i=\sqrt{2}\,e^{i\,\pi/4}.\\
\noalign{\vskip12pt}
{\rm (d)}\hskip5pt z=1-i\,\sqrt{3}.\ {\rm We\ have\ that}\ x=1\ {\rm and}\ y=-\sqrt{3},\ {\rm so}\
r=2,\ {\rm and}\\
\noalign{\vskip12pt}
\hskip20pt\theta={\rm tan}^{-1}(-\sqrt{3})=-{1\over3}\pi.\ {\rm Thus}\
1-i\,\sqrt{3}=2\,e^{-i\,\pi/3}.
\end{array}
$


\item A complex number $z=r\,e^{i\,\theta}$ can be written as
  $z=r\cos\theta+i\,r\sin\theta$.  Thus,


$\begin{array}[h!]{l}
{\rm (a)}\hskip5pt e^{-3\pi i/4}=\cos\bigl({3\over4}\pi\bigr)-i\,\sin\bigl({3\over4}\pi\bigr)=
\displaystyle{-{1+i\over\sqrt{2}}}=-{1\over2}\sqrt{2}-i\,{1\over2}\sqrt{2}\, .\\
\noalign{\vskip12pt}
{\rm (b)}\hskip5pt e^{5\pi i/4}=\cos\bigl({5\over4}\pi\bigr)+i\,\sin\bigl({5\over4}\pi\bigr)=
\displaystyle{-{1+i\over\sqrt{2}}}=-{1\over2}\sqrt{2}-i\,{1\over2}\sqrt{2}\, .\\
\noalign{\vskip12pt}
{\rm (c)}\hskip5pt 3\,e^{i}=3\cos 1+i\,\sin 1\, .\\
\noalign{\vskip12pt}
{\rm (d)}\hskip5pt \displaystyle{{1\over\sqrt{3}\,e^{\pi i/3}}=
{\sqrt{3}\over3}\,e^{-\pi i/3}=
{\sqrt{3}\over3}\cos\bigl({\textstyle{1\over3}}\pi\bigr)-
{i\,\sqrt{3}\over3}\sin\bigl({\textstyle{1\over3}}\pi\bigr)=
{\sqrt{3}\over6}-{i\over2}}\, .
\end{array}
$

%\end{enumerate}

%\subsubsection*{Tutorial}


\item Given that $z=r\,e^{i\,\theta}$, we have
\begin{eqnarray*}
(z^2)^\ast=\bigl[\bigl(r\,e^{i\,\theta}\bigr)^2\bigr]^\ast=\bigl(r^2\,e^{2i\,\theta}\bigr)^\ast=r^2\,e^{-2i\,\theta}=\bigl(r\,e^{-i\,\theta}\bigr)^2=
(z^\ast)^2\, .
\end{eqnarray*}

\item
\begin{enumerate}
\item Suppose $z_0$ is a solution of $az^2+bz+c=0$, and therefore also of $z^2+b'z+c'=0$ where $b'=b/a$ and $c'=c/a$ and $a\ne0$. Given that  $z_0^\ast$ is also a solution implies that
\[
(z-z_0)(z-z_0^\ast)=0~,
\]
or
\[
z^2-(z_0+z_0^\ast)z+|z_0|^2=0~,
\]
showing that $b'$ and $c'$ must be real. Conversely, if $a$, $b$, and $c$ are real, and $z_0$ is a solution of $az^2+bz+c=0$, then $az_0^2+bz_0+c=0$, and taking the conjugate yields
\[
a(z_0^2)^\ast+bz_0^\ast+c=0~,
\]
or
\[
a(z_0^\ast)^2+bz_0^\ast+c=0~,
\]
showing that $z_0^\ast$ is also a solution.

\item The roots of the polynomial are
  \[
  z_{\pm} = \frac{1}{2t} \left( -1 \pm \sqrt{1 - 4t} \right)
  \]
  which for $t>\frac{1}{4}$ has complex roots,
  \[
  z_{\pm} = - \frac{1}{2t} \pm i\, \frac{1}{2t}\sqrt{4t - 1} \, .
  \]
  The solutions will map out a circle centered at $z=-1$ in the complex plane.
  (To see this either show that $x={\rm Re}(z), y={\rm Im}(z)$ satisfies $(x+1)^2+y^2=1$,
  or that $|z+1|^2=1$.)
  \begin{center}
    \includegraphics[width=8cm]{PS1-1}
  \end{center}

\item Rotating the figure through $90^\circ$ is equivalent to multiplying both
  solutions by $e^{i\pi/2} = i$, thus
  \begin{align}
    z_{\pm} & = i \left( - \frac{1}{2t} \pm i\, \frac{1}{2t}\sqrt{4t - 1} \right)
    \nonumber \\
      & = \pm \frac{1}{2t}\sqrt{4t - 1} - \frac{i}{2t} \, . \nonumber
  \end{align}
  Forming the polynomial by multiplying together the two solutions gives
  \begin{align}
    p & =\left(z-z_+\right)\left(z-z_-\right)\nonumber\\
      &=
    \left( z - \frac{1}{2t}\sqrt{4t - 1} + \frac{i}{2t} \right)
    \left( z + \frac{1}{2t}\sqrt{4t - 1} + \frac{i}{2t} \right)
    \nonumber \\
     & = -\frac{1}{t}(-t z^2 - i\,z  + 1) \nonumber \, ,
  \end{align}
  thus reducing $p=0$ to $-t z^2 - i\,z + 1=0$.
  %It can be seen that this is just the original polynomial with $z$ substituted with $iz=e^{i\pi/2}z$.
  So one solution is $a(t)=-t$, $b=-i$ and $c=1$. All other solutions are multiples of this set. The solutions that were conjugate pairs for the original equation are not conjugate pairs for the new equation as the coefficients of the latter are no longer real.
  An arbitrary rotation of angle $\theta$ can be made by substituting $z_{\pm}$ with $e^{i\theta}z_{\pm}$.
\end{enumerate}
\end{enumerate}



\end{document}
"""

    katex_output = latex_to_katex(latex_input)
    print(katex_output)
