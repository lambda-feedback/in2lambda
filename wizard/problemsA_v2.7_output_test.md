## Question 1

### Question

A builder pulls with a force of \SI{300}{\N} on a rope attached to a building as shown in figure~\ref{A1:fig:Q1a}. What are the horizontal and vertical components of the force exerted by the rope at the point A?

### Answer

The horizontal component, $F_H$, is the magnitude of the force projected onto the horizontal axis, $F_H = \SI{240}{\N}$, and the vertical component, $F_V$, is the magnitude of the force projected onto the vertical axis, $F_V = \SI{180}{\N}$.

### Solution

The angle $\alpha$ between the rope and the horizontal line can be calculated using the relation between $\tan\alpha$ and the lengths of the sides of the right angled triangle as shown in figure~\ref{A1:fig:Q1b},
$$
\tan\alpha = \frac{\SI{6}{\m}}{\SI{8}{\m}} = 0.75 \, ,
$$
from which $\alpha=\ang{36.87}$.

The horizontal component, $F_H$, is the magnitude of the force projected onto the horizontal axis,
$$
F_H = \SI{300}{\N} \cos\alpha = \SI{240}{\N} \,,
$$
and the vertical component, $F_V$, is the magnitude of the force projected onto the vertical axis,
$$
F_V = \SI{300}{\N} \sin\alpha = \SI{180}{\N}\, .

## Question 2

### Question

Four forces act on a bolt as shown in figure~\ref{A1:fig:Q2}. Determine the resultant of the forces on the bolt.

### Answer

The resultant force is $R_H = \SI{199.1}{\N}$ horizontally and $R_V = \SI{14.3}{\N}$ vertically.

### Solution

To obtain the resultant force, the projection of the resultant on the vertical and horizontal axes is determined as the sum of the projections of the four forces onto the respective axes,
$$
R_H = F_1 \cos\ang{30} - F_2\sin\ang{20} + F_4 \cos\ang{15} = \SI{199.1}{\N} \,,
$$
$$
R_V = F_1 \sin\ang{30} +F_2 \cos\ang{20}-F_3 -F_4\sin\ang{15} = \SI{14.3}{\N} \, .
$$
The angle with the horizontal then follows from
$$
\frac{R_V}{R_H} = \frac{R\sin\alpha}{R\cos\alpha} = \tan\alpha = 0.0718\, .
$$
Hence, $\alpha=\ang{4.1}$. The magnitude of the resultant follows from,
$$
|R| = \sqrt{R_H^2+R_V^2} = \SI{199.6}{\N}.

## Question 3

### Question

A car is being towed with two ropes as shown in figure~\ref{A1:fig:Q3}. If the resultant of the two forces is a \SI{30}{\N} force parallel to the long axis of the car, find:
1. the tension in each of the ropes, if $\alpha = \ang{30}$.
2. the value of $\alpha$ such that the tension in rope, $T_2$ is minimal.

### Answer

1. $T_1 = \SI{19.58}{\N}$, $T_2 = \SI{13.39}{\N}$.
2. $\alpha_{min} = \ang{70}$.

### Solution

In order for the resultant force to be a force with magnitude \SI{30}{\N} oriented along the horizontal, the following conditions must be true,
$$
T_2 \cos\alpha + T_1 \cos\ang{20} = \SI{30}{\N} \,,
$$
$$
T_2 \sin\alpha - T_1 \sin\ang{20} = 0 \,.
$$
Hence,
$$
T_2 = T_1\frac{\sin\ang{20}}{\sin\alpha} \,,
$$
$$
\left( T_1 \frac{\sin\ang{20}}{\sin\alpha} \right) \cos\alpha + T_1\cos\ang{20} = \SI{30}{\N} \,.
$$
When $\alpha=\ang{30}$, this yields
$$
T_1 = \SI{19.58}{\N} \,,
$$
$$
T_2 = \SI{13.39}{\N} \,.
$$

Substituting the expression for $T_1$ into the expression for $T_2$ allows us to determine $T_2$ as a function of $\alpha$,
$$
T_2 = \frac{\SI{30}{\N}}{\frac{\sin\ang{20}}{\tan\alpha} + \cos\ang{20}} \frac{\sin\ang{20}}{\sin\alpha} \,.
$$
Examining the form of this, we can see that $T_2$ will be minimal at $\alpha_{min}$ when $\left(\cos\alpha + \frac{\sin\alpha}{\tan\ang{20}}\right)$ is maximal. Searching for maximal stationary points in the usual manner,
$$
\frac{\mathrm{d}}{\mathrm{d}\alpha} \left(\cos\alpha + \frac{\sin\alpha}{\tan\ang{20}}\right) = 0 \,,
$$
$$
\tan\alpha_{min} = \frac{1}{\tan\ang{20}} \Rightarrow \alpha_{min} = \ang{70} \,.
$$

## Question 4

### Question

A \SI{30}{\N} force acts on the end of a \SI{3}{\m} lever as shown in figure~\ref{A1:fig:Q4a}. Determine the moment of the force about the point O.

### Answer

The moment of the force about point O is \SI{30.8}{\N}.

### Solution

We can make many problems easier by choosing a suitable set of axes. Looking at the special directions of this system, we can choose to orient the x-axis parallel to the line connecting point $O$ and the point where the force acts and the y-axis perpendicular to this. The moment of the force is then given by
$$
M = F_y\, d = \SI{30}{\N} \sin\ang{20} \SI{3}{\m} = \SI{30.8}{\N} \,.
$$

## Question 5

### Question

A \SI{4.8}{\m} beam is subjected to the system of forces as shown in figure~\ref{A1:fig:Q5a}. Reduce the given system of forces to:
1. an equivalent force--couple system at A.
2. an equivalent force--couple system at B.
3. a single force or resultant.

### Answer

1. Equivalent force--couple system at A: \SI{600}{\N} downwards and a couple of \SI{1880}{\N\m} acting clockwise about A.
2. Equivalent force--couple system at B: \SI{600}{\N} downwards and a couple of \SI{1000}{\N\m} acting anticlockwise about B.
3. The resultant force is \SI{600}{\N} acting \SI{3.13}{\m} from A.

### Solution

The first step is to calculate the resultant force. This is common to all three parts of the problem. Choosing the x-axis to be parallel to the beam, and the y-axis perpendicular to the beam, the resultant is found to be
$$
R\left(\uparrow\right): \sum\, F_y = \SI{150}{\N} - \SI{600}{\N} + \SI{100}{\N} - \SI{250}{\N} = \SI{-600}{\N} \,.
$$
As all forces are acting perpendicular to the beam, the moment due to each force is the product of the force magnitude and the distance between the point of action and the pivot. Hence, the moment about the point $A$ is given by
$$
M_A = \SI{-150}{\N}\times \SI{0}{\m} + \SI{600}{\N}\times \SI{1.6}{\m} - \SI{100}{\N}\times \SI{2.8}{\m} + \SI{250}{\N} \times \SI{4.8}{\m} = \SI{1880}{\N\m} \,.
$$
Hence, the loading shown in figure~\ref{A1:fig:Q5a} is equivalent to a force of \SI{600}{\N} downwards and a couple of \SI{1880}{\N\m} acting clockwise about $A$.

For the equivalent force-couple system evaluated at the point B, the resultant force is the same but a new equivalent couple must be calculated.
$$
M_B = \SI{150}{\N}\times \SI{4.8}{\m} - \SI{600}{\N}\times \SI{3.2}{\m} + \SI{100}{\N}\times \SI{2}{\m} - \SI{250}{\N} \times \SI{0}{\m} = \SI{-1000}{\N\m} \,.
$$
Hence, the loading shown in figure~\ref{A1:fig:Q5a} is equivalent to a force of \SI{600}{\N} downwards and a couple of \SI{1000}{\N\m} acting anticlockwise about $B$.

To reduce the system of forces shown in figure~\ref{A1:fig:Q5a} to a single resultant force with no couple, we must consider the resultant force to act at some unknown point $X$ a distance $x$ \si{\m} from $A$ where the equivalent couple of the system is zero. The moment about $X$ is given by
$$
M_X = \SI{150}{\N}\times x \, \si{\m} + \SI{600}{\N}\times (1.6-x) \, \si{\m} - \SI{100}{\N}\times (2.8-x) \, \si{\m} + \SI{250}{\N} \times (4.8-x) \, \si{\m} = 0\,.
$$
Rearranging for $x$ gives
$$
x = \frac{-(600\times 1.6 -100\times 2.8 + 250\times 4.8)\, \si{\N}}{(150 -600 +100-250) \, \si{\m}} = \frac{\SI{-1880}{\N\m}}{\SI{-600}{\N}} = \SI{3.13}{\m} \,.
$$

## Question 6

### Question

A beam of length \SI{4}{\m} is loaded in the various ways shown in figure~\ref{A1:fig:Q6a}. Find the two loadings which are equivalent.

### Answer

The equivalent loadings are scenarios (c) and (f).

### Solution

To consider whether different loading systems are statically equivalent, it is convenient to consider the effect about a single common reference point by calculating the equivalent force-couple resultant. This requires moving the point at which forces act and hence accounting for the moment such forces induce about the reference point. A detailed procedure for case \textit{(a)} is shown in figure~\ref{A1:fig:Q6b}. The moment of \SI{1500}{\N\m} is equivalent to a set of forces acting at either end of the beam, one acting upward and one acting downward so as to have no net resultant force. The magnitude of this force is given by
$$
M_R = \SI{1500}{\N\m} = F \times \SI{4}{\m} \Rightarrow F = \frac{\SI{1500}{\N\m}}{\SI{4}{\m}} = \SI{375}{\N} \,.
$$
Applying either method to all the loading scenarios yields the results shown in figure~\ref{A1:fig:Q6c}, showing scenarios \textit{(c)} and \textit{(f)} to be equivalent.

## Question 7

### Question

Two forces, $P$ and $Q$ of magnitude $P=\SI{100}{\N}$ and $Q=\SI{120}{\N}$ are applied to the aircraft connection shown in figure~\ref{A2:fig:Q1}. Knowing that the connection is in equilibrium, determine the tensions $T_1$ and $T_2$.

### Answer

$T_1 = \SI{76.11}{\N}$, $T_2 = \SI{79.16}{\N}$.

### Solution

Equilibrium requires that there is no net force in any direction and no net moment. However, it is clear that the line of action of all forces intersect in a common point, hence the system of forces cannot cause any rotation. Furthermore, all forces act within the plane of the paper, hence the only remaining equations for equilibrium are
$$
\sum F_x=0 \,,
$$
$$
\sum F_y=0 \,.
$$

Choosing the $x$-axis parallel to the line of action of $T_1$ and the y-axis perpendicular with this, the equilibrium equations can be made explicit as
$$
\sum F_x = -Q\cos\ang{15} + T_2\cos\ang{60} + T_1 = 0 \,,
$$
$$
\sum F_y = Q\sin\ang{15} + T_2\sin\ang{60} - P = 0 \,.
$$

Solving this for $T_1$ and $T_2$ yields
$$
T_2 = \frac{P-Q\sin\ang{15}}{\sin\ang{60}} = \frac{\SI{100}{\N} - \SI{120}{\N} \times 0.2588}{\frac{\sqrt{3}}{2}} = \SI{79.16}{\N} \,,
$$
$$
T_1 = Q\cos\ang{15} - T_2\cos\ang{60} = \SI{120}{\N} \times 0.966 - \frac{\SI{79.16}{\N}}{2} = \SI{76.11}{\N} \,.
$$

## Question 8

### Question

A cantilever beam is loaded as shown in figure~\ref{A2:fig:Q2a}. The beam is fixed at the left hand end and is free at the right hand end. Determine the reaction at the fixed end.

### Answer

$R_x = 0$, $R_y = \SI{1400}{\N}$, $M_z = \SI{-4000}{\N\m}$.

### Solution

To find the reaction in the fixed end, a free body diagram of the loading scenario is drawn. A fixed end stops displacements occurring in both the vertical and horizontal directions thus yielding a reaction in both these direction, $R_x$, $R_y$. A fixed end also stops rotations from occurring and hence will also impart a reaction moment if required, $M_z$. 

Using the equilibrium equation,
$$
R\left(\rightarrow\right): -R_x = 0 \Rightarrow R_x = 0 \,,
$$
$$
R\left(\uparrow\right): R_y = \SI{800}{\N} + \SI{400}{\N} + \SI{200}{\N} = \SI{1400}{\N} \,,
$$
$$
M\raisebox{1.5pt}{\big(}\overset{\\curvearrowright}{\text{Fixed}}\raisebox{1.5pt}{\big)}: 0 = M_z + \SI{800}{\N} \times \SI{1.5}{\m} + \SI{400}{\N} \times \SI{4}{\m} + \SI{200}{\N} \times \SI{6}{\m} \,.
$$
Thus, we find $M_z = \SI{-4000}{\N\m}$.

## Question 9

### Question

A \SI{100}{\N} force acts on a block of weight \SI{300}{\N} placed on an inclined plane as shown in figure~\ref{A2:fig:Q3a}. The coefficient of static friction between the block and the plane is $\mu=0.25$. Determine whether the block is in equilibrium.

### Answer

The block will slide down the inclined plane.

### Solution

To ascertain whether the block is in equilibrium, first the situation is translated into a free body diagram where the support of the slope, $R$, and the contribution from friction, $R_F$ are added. Choosing the x-axis parallel to the slope, and the y-axis perpendicular to it, the equilibrium relations give
$$
\sum F_x = 0 \Rightarrow \SI{100}{\N} - \SI{300}{\N}\sin\alpha + R_F \,,
$$
$$
\sum F_y = 0 \Rightarrow R - \SI{300}{\N}\cos\alpha \,.
$$

Solving for $R$ and $R_F$ we find $R = \SI{240}{\N}$ and $R_F = \SI{80}{\N}$. However, if $R_F$ is due to static friction, then the maximum value it can exert is given by
$$
R_{F,max} = \mu R = 0.25 \times \SI{240}{\N} = \SI{60}{\N} \,.
$$
This is less than the value required for equilibrium and hence the block will slide down the inclined plane.

## Question 10

### Question

A \SI{10}{\kg} joist of length \SI{4}{\m} is raised by pulling on a rope as shown in figure~\ref{A2:fig:Q4a}. Find the tension $T$ in the rope and the reaction force(s) at point A.

### Answer

$T = \SI{69.3}{\N}$, $R_{Ax} = \SI{-66.9}{\N}$, $R_{Ay} = \SI{-115.9}{\N}$.

### Solution

To find the tension $T$ and the reaction(s) at A, we must first express the mass of the beam (\SI{10}{\kg}) as a force, its weight. In the gravitational field of the Earth, a \SI{10}{\kg} mass would experience an acceleration of \SI{9.8}{\m\s^{-2}} and hence a force of $\SI{10}{\kg} \times \SI{9.8}{\m\s^{-2}} = \SI{98}{\N}$ acting directly downwards. This force will act at the centre of mass which is, by symmetry, located halfway along the joist.

Applying the equilibrium equations yields
$$
\sum F_x = 0 \Rightarrow -T\cos\ang{15} - R_{Ax} = 0 \,,
$$
$$
\sum F_y = 0 \Rightarrow -T\sin\ang{15} - R_{Ay} - \SI{98}{\N} = 0 \,,
$$
$$
\left(\sum M_z\right)_A = 0 \Rightarrow \SI{98}{\N} \times \SI{2}{\m} \cos\ang{45} - T\sin\ang{30} \times \SI{4}{\m} \,.
$$

Solving for $R_{Ax}$, $R_{Ay}$ and $T$ yields,
$$
T = \SI{98}{\N} \frac{\SI{2}{\m}}{\SI{4}{\m}} \frac{\cos\ang{45}}{\sin\ang{30}} = \frac{\SI{98}{\N}}{\sqrt{2}} = \SI{69.3}{\N} \,,
$$
$$
R_{Ax} = -T\cos\ang{15} = \SI{-69.3} \times 0.966 = \SI{-66.9}{\N} \,,
$$
$$
R_{Ay} = -T\sin\ang{15} - \SI{98}{\N} = \SI{-69.3}{\N} \times 0.259 - \SI{98}{\N} = \SI{-115.9}{\N} \,.
$$

## Question 11

### Question

Using the method of joints, determine the force in each member of the truss as shown in figure~\ref{A3:fig:Q5a}.

### Answer

The forces in the members are: $F_1 = \SI{1500}{\N}$, $F_2 = \SI{-2500}{\N}$, $F_3 = \SI{2500}{\N}$, $F_4 = \SI{-3000}{\N}$, $F_5 = \SI{-3750}{\N}$, $F_6 = \SI{5250}{\N}$, $F_7 = \SI{-8750}{\N}$.

### Solution

The first step to find the force in each member of the truss is to replace all supports by their reactions. The roller at $E$ only resist a vertical displacement and hence only gives a vertical reaction, whereas the pivot at $C$ can resist displacements in both the horizontal and vertical direction and hence gives two reactions. For each of reference, each member has been numbered as shown in the free body diagram of the truss.

The free body diagram also shows that all the diagonal members form the same angle, $\alpha$, with the horizontal. By examining the dimensions of the truss and forming a right-angle triangle for member $2$, we can see that $\sin\alpha=0.8$ and $\cos\alpha=0.6$.

The next step is to make some starting assumptions about the nature of the forces acting on each of the members. It is assumed here that all members are in tension, hence, by Newton III, each of the members pulls on the joints to which it is attached.

Then, we note that for overall equilibrium to be achieved, we require each joint to individually be in equilibrium. Hence we can write down two equilibrium equations for each joint.

This is a set of 10 equations with 10 unknowns and therefore it is not impossible to solve. Solving by substitution yields
$$
F_2 = \SI{-2500}{\N} \,,
$$
$$
F_1 = \SI{1500}{\N} \,,
$$
$$
F_3 = \SI{2500}{\N} \,,
$$
$$
F_4 = \SI{-3000}{\N} \,,
$$
$$
F_5 = \SI{-3750}{\N} \,,
$$
$$
F_6 = \SI{5250}{\N} \,,
$$
$$
F_7 = \SI{-8750}{\N} \,.
$$

## Question 12

### Question

Examine the trusses shown in figure~\ref{A3:fig:Q6ab} and explain, without calculation, which members you believe will be in tension and which in compression.

### Answer

Members in tension: diagonal members. Members in compression: horizontal member.

### Solution

To determine whether a member will be in tension or compression we must consider the expected deformation of the structure. For the first truss, the weight pulling down on the structure will attempt to elongate the diagonal members and hence these are expected to be in tension. The horizontal member is expected to be in compression.

Predicting the type of load in horizontal member is a little more tricky. If the member is in tension then this will be moving the supports further apart effectively elongating the diagonal members or lifting the load upward if the diagonal members are considered to be of fixed length. Both of these would require an addition of energy into the system, the opposite of what would be expected. If the member is in compression then the reverse would happen, either the elongation of the diagonal members would reduce or the load would be lowered, both lower energy states. Hence we would expect the horizontal member to be in compression.

## Question 13

### Question

Using the method of joints, calculate the force in each member of the two trusses.

### Answer

For the first truss: $F_{AB} = 3.25 F$, $F_{AC} = 3.75 F$, $F_{BC} = 3 F$.

### Solution

By applying the method of joints, the actual forces in the members are found as follows,
$$
F_{AB} = \frac{F}{\cos\beta\left(\tan\gamma -\tan\beta\right)} = 3.25 F \,,
$$
$$
F_{AC} = \frac{F}{\cos\gamma\left(\tan\gamma -\tan\beta\right)} = 3.75 F \,,
$$
$$
F_{BC} = \frac{F}{\tan\gamma -\tan\beta} = 3 F \,.
$$

## Question 14

### Question

Determine the components of the forces acting on each of three members in the frame shown in figure~\ref{A3:fig:Q7a}. The distance between all adjacent joints is $L$.

### Answer

$N_A = \frac{-W}{4}$, $N_E = \frac{5W}{4}$.

### Solution

Before we begin, we must note that this is a frame, not a truss and so not all forces are applied at joints between beams. Thus, when we use the method of joints, we cannot assume that the forces acting on a beam will act along the length of the beam.

We start by finding the reaction forces that keep the frame as a whole in equilibrium,
$$
R\left(\rightarrow\right): 0 = N_A + N_E - W \,,
$$
$$
R\left(\uparrow\right): 0 = -N_E L + 2N_E L \,.
$$

We next divide the frame into beams and joints, drawing a free body diagram for each member and joint. We can now begin to enforce equilibrium for each member in turn. For the beam ABC,
$$
R\left(\rightarrow\right): 0 = B_x + C_x \,,
$$
$$
R\left(\uparrow\right): 0 = N_A + B_y + C_y \,,
$$
$$
M\raisebox{1.5pt}{\big(}\overset{\curvearrowright}{A}\raisebox{1.5pt}{\big)}: 0 = -B_y L \cos\ang{60} + B_x L \sin\ang{60} - C_y \cdot 2L \cos\ang{60} + C_x \cdot 2L \sin\ang{60} \,.
$$

For the beam CDE,
$$
R\left(\rightarrow\right): 0 = C'_x + D'_x \,,
$$
$$
R\left(\uparrow\right): 0 = N_E - C'_y + D_y \,,
$$
$$
R\left(\rightarrow\right): 0 = B'_x + D'_x \,,
$$
$$
R\left(\uparrow\right): 0 = B'_y + D'_y + W \,,
$$
$$
M\raisebox{1.5pt}{\big(}\overset{\curvearrowright}{F}\raisebox{1.5pt}{\big)}: 0 = D'_y L + C'_y \cdot 2L \,.
$$

Each joint must also be in equilibrium, yielding another six equations to relate together the forces on the members. We now have the ingredients to substitute the equations for the beams into the equations for the joints, giving us the final values for the forces on each beam.

## Question 15

### Question

Determine the components of the forces acting on each member of the frame shown in figure~\ref{A3:fig:Q8a}.

### Answer

$N_1 = \frac{3}{2}F$, $N_2 = 2F$, $N_3 = -F$.

### Solution

Although all the beams are clearly connected by pin joints, the force does not act at a joint, making this a frame, not a truss. Hence, it is no longer acceptable to assume that the forces will act along the length of the members in the frame. To find the forces which act on the members of the frame we must first ensure the overall equilibrium of the frame.

Resolving and taking moments about the pivot,
$$
R\left(\rightarrow\right): 0 = R \sin\theta \Rightarrow \theta = 0 \,,
$$
$$
R\left(\uparrow\right): 0 = N + R \cos\theta - F \Rightarrow R = F - N \,.
$$

Substituting the value of $\theta$, we get $F = N + R$. Now, taking moments about the pivot,
$$
0 = 3LN - 4LF \Rightarrow N = \frac{4F}{3} \,.
$$

To find the internal forces and moments acting at the plane $a$, first consider the free body diagram for the upper beam. Asserting equilibrium,
$$
R\left(\rightarrow\right): 0 = R' \sin\theta \Rightarrow \theta = 0 \,,
$$
$$
R\left(\uparrow\right): 0 = R' \cos\theta - F + N' \,.
$$

Substituting the value of $\theta$, we get $F = N' + R'$. Now taking moments about the pivot,
$$
0 = 2LN' - 4LF \Rightarrow N' = 2F \,.
$$

Thus, we find $R' = F - N' = -F$.
