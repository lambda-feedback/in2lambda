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
        #replace with nothing
        r'\\label{.*?}': r'', #delete label and argument
        r'\\ref': r'', #delete ref and argument
        r'\\eqref': r'',
        r'\\begin{figure}': r'', #delete centerline and argument
        r'\\end{figure}': r'', #delete centerline and argument
        r'\\begin{enumerate}': r'',
        r'\\end{enumerate}': r'',
        r'\\item':r'',

        r'\\caption{.*?}': r'', #delete caption and argument 
        r'\\centerline': r'', #delete centerline and argument 


        r'\\bigskip': r'',
        r'\\medskip': r'',
        r'\\smallskip': r'', #skipping functions are unsupported
        r'\\noindent': r'',
        r'\\vrulefill': r'',
        r'\\vfill': r'',
        r'\\vfil': r'',
        r'\\hrulefill': r'',
        r'\\hfill': r'',
        r'\\hfil': r'',
        r'\\hline': r'',
        r'\\vline': r'',
        r'\\setlength{.*?}': r'',
        r'\\hskip': r'',
        r'\\vskip': r'',
        r'\[h\]': r'',
        r'\[t\]': r'',
        r'\[b\]': r'',
        r'\[p\]': r'',
        r'\[!\]': r'', #remove alignments
        r'\[H\]': r'',
        r'-[0-9]*pt':'', #removes digits followed by pt
        r'[0-9]*pt':'', 
        #r'-[0-9]*in':'',
        #r'[0-9]*in':'',  NOTE: GETS RID OF ALL in
        r'\{}':'', #removes lone {} brackets

        #replace with something
        r'\\begin{eqnarray}': r'\\begin{align}', #KaTeX does not support eqn array: replace with align
        r'\\end{eqnarray}': r'\\end{align}',
        r'\\begin{eqnarray*}': r'\\begin{align*}', #KaTeX does not support eqn array: replace with align
        r'\\end{eqnarray*}': r'\\end{align*}',
            
    }

    #replace the incompatible functions with their KaTeX equivalents using re.sub
    for old, new in replacements.items():
        latex_string = re.sub(old, new, latex_string)


    while latex_string.startswith('{') and latex_string.endswith('}'):
        latex_string = latex_string[1:-1]  # Remove the first and last characters


    return latex_string

    # Remove extra outer curly brackets if the first character is a curly bracket
    
    

latex_input_ = r'''\begin{document}

\centerline{\Large Complex Numbers, Functions and Ordinary Differential Equations}
\bigskip\bigskip


\noindent
Problem sheet 4\hfill 2023

\vskip-9pt\hrulefill

\bigskip

%\subsubsection*{For tutorials}

\begin{enumerate}
\item When you do the Vector Fields and Electricity and Magnetism module next term, you will encounter the Lorentz force law for a charge $q$ of mass $m$ moving in a magnetic field $\bf B$:
    \begin{equation}
    m \frac{d{\bf v}}{dt} = q{\bf v}\times {\bf B}\, .
    \end{equation}
    \begin{enumerate}
\item Show that for a charge moving in the $x$-$y$ plane under the influence of a magnetic field ${\bf B}=B{\bf k}$ the equations of motion are
  \begin{equation}
  m\frac{dv_x}{dt} = qv_yB,~~~m\frac{dv_y}{dt} = -qv_xB~.
  \label{eq:mag40b}
  \end{equation}
\item By introducing the complex variable ${\tilde v}=v_x+iv_y$, show that Eqs. \eqref{eq:mag40b} may be written as
\begin{equation}
d{\tilde v}/{dt}=-i\omega_c {\tilde v}\, ,
\end{equation}
where $\omega_c = \frac{qB}{m}$.
\item By solving this equation show that the general solution to Eqs. \eqref{eq:mag40b} is
\begin{align}
  v_x(t)=\frac{dx}{dt} &= v_x(0)\cos\omega_ct+v_y(0)\sin\omega_ct,\nonumber\\
  v_y(t)=\frac{dy}{dt} &= -v_x(0)\sin\omega_ct+v_y(0)\cos\omega_ct,\label{eq:mag40g}
  \end{align}
  where $v_x(0)$ and $v_y(0)$ are the charge's initial velocity components.
\item Integrate these equations again to show that the trajectory of the charge is given by
\begin{align}
  x(t)&=  x(0)+\omega_c^{-1}\left[v_x(0)\sin\omega_ct+v_y(0)(1-\cos\omega_ct)\right],\nonumber\\
  y(t)&=  y(0)+\omega_c^{-1}\left[v_y(0)\sin\omega_ct-v_x(0)(1-\cos\omega_ct)\right]~,\label{eq:mag40h}
  \end{align}
  where $x(0)$ and $y(0)$ are the coordinates of the charge's initial position.
\item Show that the last two equations can be recast as
\begin{equation}
  \left[x-x(0)-v_y(0)/\omega_c\right]^2 + \left[y-y(0)+v_x(0)/\omega_c\right]^2 = v^2/\omega_c^{2},
  \label{eq:mag40i}
  \end{equation}
where $v^2=v^2_x(0)+v^2_y(0)$.
\item Using the above two equations, describe the motion of the charge. What meaning can you assign to a change in sign of $\omega_0$ induced by a change in sign of the charge, $q$?
\end{enumerate}

\item This question addresses the following: is it easier to balance a snooker cue on its tip (Fig. \ref{fig:cue}(a)) or on its base (Fig. \ref{fig:cue} (b))?
\begin{figure}
/{\includegraphics[width=9cm]{SnookerCueB}}
\caption{\label{fig:cue}(a) Balancing cue on tip, (b) Balancing cue on base.}
\end{figure}
The equation we will need is
\begin{equation}
I\frac{d^2\theta}{dt^2}=r \sin \theta Mg~,
\label{thetaeq}
\end{equation}
where $I$ is called the {\em moment of inertia}, and $r$ is the distance from the pivot point to the cue's centre of mass. The centre of mass is located at $3L/4$ from the tip of the cue, where $L$ is the cue's length. For (a) $I\approx 3ML^2/5$, while for (b) $I \approx ML^2/10$.
\begin{enumerate}
\item Show that for {\em small} angles the equation of motion can be written as
\begin{equation}
\frac{d^2\theta}{dt^2}\approx p^2 \theta~,
\label{thetaeqB}
\end{equation}
writing down an expression for $p$ for the two cases.
\item Write down the general solution to Eq. \eqref{thetaeqB} in terms of exponential functions.
\item Show that if the cue starts at rest with a very small angular deflection $\delta\theta_0$, the solution becomes
\[\theta(t)=\delta\theta_0\cosh pt~.\]
\item On the same axes sketch $\theta(t)$ for the two cases.
\item Bearing in mind that our solution is only valid for small angles, is it easier to balance a cue on its tip or its base?
\end{enumerate}

\item
A Foucault pendulum consists of a mass suspended
from a cord of length $l$ suspended vertically (the $z$ direction)
at latitude $\lambda$, the rotation plane being free to move in
the $x$-$y$ plane (see Figure \ref{Fig:McCall9_8}).
\begin{figure}[h]
\centerline{\includegraphics[width=7cm]{Foucault}}
\caption{\label{Fig:McCall9_8}Foucault's pendulum.}
\end{figure}
For small amplitude swings the equations of motion are
\begin{eqnarray}
{\ddot x} - 2\Omega {\dot y} + \omega_0^2x&=&0~, \nonumber\\
{\ddot y} + 2\Omega {\dot x} + \omega_0^2y&=&0~,\nonumber
\end{eqnarray}
where $\omega_0^2=g/l, \Omega = \omega\sin\lambda$ and $\omega$ is the angular rate of the earth's rotation. Note that $\omega_0 \gg \Omega$.
\begin{enumerate}

\item By defining a {\em complex} displacement $z=x+iy$, show that the above equations can be written as the single complex equation
\[
{\ddot z}+2i\Omega {\dot z} +\omega_0^2 z =0~.
\]
\item Show that the roots of the characteristic equation are
\[
m = i\left[-\Omega \pm \left(\Omega^2+\omega_0^2\right)^{1/2}\right]\approx i\left(-\Omega \pm \omega_0\right)~,
\]
and that the general solution is therefore
\[
z(t) \approx \left[z_+e^{i\omega_0 t}+z_-e^{-i\omega_0t}\right]e^{-i\Omega t}~,
\]
where $z_{\pm}$ are complex constants determined by the initial conditions.


\item Using the above approximate solution, show that if the pendulum starts from rest ${\dot z}(0)=0$, with  displacement $z(0)=a$ (i.e. real), then (hint: remember $\Omega \ll \omega_0$)
\[
z_+ \approx z_- \approx \frac{a}{2}~.
\]

\item By taking the real and imaginary parts of the complex solution show that
\begin{eqnarray*}
x(t) & \approx &  a\cos\omega_0 t\cos\Omega t~,\label{Foucaultx}\\
y(t) & \approx & -a\cos\omega_0 t\sin\Omega t~.\label{Foucaulty}
\end{eqnarray*}

\item Use the above solution to make a sketch of the pendulum's motion in the $x$-$y$ plane.
For a more detailed analysis (in which the approximations made here are lifted) - see MWM p.207.

\end{enumerate}


\item Every rigid body (e.g. a brick - see Fig. \ref{Fig:brick})
\begin{figure}[h]
\centerline{\includegraphics[width=9cm]{Brick}}
\caption{\label{Fig:brick}A rotating body has 3 principal axes}
\end{figure}
has three {\em principal axes} to which there are associated three {\em principal moments of inertia}, $I_{1,2,3}$. In this problem we will assume that all three principal moments are distinct $I_1 \ne I_2 \ne I_3$.  When the body spins its  {\em angular velocity} considered as a vector $\boldsymbol \omega$, has components $(\omega_1,\omega_2,\omega_3)$ for rotations around the three  principal axes respectively. In the absence of any external torque the equations of motion are (known as Euler's equations)
    \begin{eqnarray}
I_1\frac{d\omega_1}{dt} &=& \omega_2\omega_3\left(I_2-I_3\right)~,\label{Euler1}\\
I_2\frac{d\omega_2}{dt} &=& \omega_3\omega_1\left(I_3-I_1\right)~,\label{Euler2}\\
I_3\frac{d\omega_3}{dt} &=& \omega_1\omega_2\left(I_1-I_2\right)~,\label{Euler3}
\end{eqnarray}
\begin{enumerate}
\item Imagine the body is rotating mainly about principal axis 3, so that ${\boldsymbol \omega} = \omega(\delta_1,\delta_2,1)$ where $|\delta_1|,|\delta_2| \ll 1$. Keeping terms to first order in $\delta_{1,2}$, show that the equations of motion reduce to (approximately)
    \begin{eqnarray}
I_1\frac{d\delta_1}{dt} &\approx& \left(I_2-I_3\right)\omega \delta_2~,\label{Euler1perturb}\\
I_2\frac{d\delta_2}{dt} &\approx& \left(I_3-I_1\right)\omega \delta_1~.\label{Euler2perturb}
\end{eqnarray}
\item Hence show that
\begin{eqnarray}
\frac{d^2\delta_1}{dt^2} - q^2 \delta_1  &=& 0~,\label{Euler1perturbA}\\
\frac{d^2\delta_2}{dt^2} - q^2 \delta_2  &=& 0~,\label{Euler2perturbB}
\end{eqnarray}
where
\begin{equation}
q^2 = \frac{\left(I_3-I_1\right)\left(I_2-I_3\right)}{I_1I_2}\omega^2~.
\end{equation}
\item Using what you know about the nature of solutions to equations \eqref{Euler1perturbA} and \eqref{Euler2perturbB} for different signs of $q^2$ deduce that the motion is {\em stable} (i.e. $\delta_{1,2}$ do not grow exponentially) if either $I_3 < I_{1,2}$, or $I_3 > I_{1,2}$, and is {\em unstable} (i.e. $\delta_{1,2}$ do grow exponentially) if $I_3$ lies between the other two principal moments, i.e. $I_1 < I_3 < I_2$ say.

\item Try it with a matchbox!
\end{enumerate}
\end{enumerate}


\end{document}'''


#print(latex_input_)
katex_output = latex_to_katex(latex_input_)
print(katex_output)

