import json
from copy import deepcopy
import zipfile

def converter(template,ListQuestions):
    #Create output by copying template
    output=deepcopy(template)

    #counter for number of loops
    count=1

    for i in range(0,len(ListQuestions)):

        #add title to the question file
        if ListQuestions[i]['Title']!="":
            output['title']=ListQuestions[i]['Title']
        else:
            output['title']="Question "+str(count) 

        #add main text to the question file
        output['masterContent']['blocks'][0]['data']=ListQuestions[i]['MainText']

        #add parts to the question file
        output['parts'][0]['content']['blocks'][0]['data']=ListQuestions[i]['Parts'][0]['Text']
        output['parts'][0]['workedSolution'][0]['content']['blocks'][0]['data']=ListQuestions[i]['Parts'][0]['Answer']
        for j in range(1,len(ListQuestions[i]['Parts'])):
             output['parts'].append(deepcopy(template['parts'][0]))
             output['parts'][j]['content']['blocks'][0]['data']=ListQuestions[i]['Parts'][j]['Text']
             output['parts'][j]['workedSolution'][0]['content']['blocks'][0]['data']=ListQuestions[i]['Parts'][j]['Answer']

        #Output file
        filename="Question "+str(count) 
        with open(filename+'.json','w') as file:
            json.dump(output,file)  
        with zipfile.ZipFile(filename+'.zip', "w") as zipf:
                        zipf.write(filename+'.json', arcname=filename+'.json')
        #increase counter
        count=count+1


def main():
    ListQuestions=[{   'MainText': 'A car is being towed with two ropes as shown in figure\xa0. '
                'If the resultant of the two forces is a 30\xa0N force '
                'parallel to the long axis of the car, find:',
    'Parts': [   {   'Answer': 'In order for the resultant force to be a force '
                               'with magnitude 30\xa0N oriented along the '
                               'horizontal, the following conditions must be '
                               'true,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_2 \\cos\\alpha + T_1 \\cos\\ang{20} &= '
                               '\\SI{30}{\\N}    \\\\\n'
                               '    T_2 \\sin\\alpha - T_1 \\sin\\ang{20} &= 0 '
                               '\\,.\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'Hence,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_2 &=  '
                               'T_1\\frac{\\sin\\ang{20}}{\\sin\\alpha}  \\\\\n'
                               '    \\left(  T_1 '
                               '\\frac{\\sin\\ang{20}}{\\sin\\alpha} \\right) '
                               '\\cos\\alpha &+ T_1\\cos\\ang{20} = '
                               '\\SI{30}{\\N} \\nonumber \\\\\n'
                               '    T_1 &=  '
                               '\\frac{\\SI{30}{\\N}}{\\frac{\\sin\\ang{20}}{\\tan\\alpha} '
                               '+ \\cos\\ang{20}}  \\,. \n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'When $\\alpha=\\ang{30}$, this yields\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_1&=\\SI{19.58}{\\N}\\\\\n'
                               '    T_2&=\\SI{13.39}{\\N}\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               '\n'
                               '\n'
                               'Substituting the expression for $T_1$, '
                               'equation\xa0, into the expression for $T_2$, '
                               'equation\xa0 allows us to determine $T_2$ as a '
                               'function of $\\alpha$,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_2 '
                               '&=\\frac{\\SI{30}{\\N}}{\\frac{\\sin\\ang{20}}{\\tan\\alpha} '
                               '+ \\cos\\ang{20}}    '
                               '\\frac{\\sin\\ang{20}}{\\sin\\alpha} '
                               '\\nonumber   \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}    '
                               '{\\sin\\ang{20}\\frac{\\cos\\alpha}{\\sin\\alpha} '
                               '+ \\cos\\ang{20}}  '
                               '\\frac{\\sin\\ang{20}}{\\sin\\alpha} '
                               '\\nonumber \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}    '
                               '{\\sin\\ang{20}\\frac{\\cos\\alpha}{\\sin\\alpha}\\frac{\\sin\\alpha}{\\sin\\ang{20}} '
                               '+ '
                               '\\cos\\ang{20}\\frac{\\sin\\alpha}{\\sin\\ang{20}}}    '
                               '\\nonumber \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}    '
                               '{\\cancel{\\sin\\ang{20}}  '
                               '\\frac{\\cos\\alpha}   '
                               '{\\cancel{\\sin\\alpha}}   '
                               '\\frac{\\cancel{\\sin\\alpha}}{\\cancel{\\sin\\ang{20}}} '
                               '+ '
                               '\\cos\\ang{20}\\frac{\\sin\\alpha}{\\sin\\ang{20}}}    '
                               '\\nonumber \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}{\\cos\\alpha + '
                               '\\frac{\\sin\\alpha}{\\tan\\ang{20}}} \\,.\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'Examining the form of this, we can see that '
                               '$T_2$ will be minimal at $\\alpha_{min}$ when '
                               '$\\left(\\cos\\alpha + '
                               '\\frac{\\sin\\alpha}{\\tan\\ang{20}}\\right)$ '
                               'is maximal. Searching for maximal stationary '
                               'points in the usual manner,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    \\frac{\\mathrm{d}}{\\mathrm{d}\\alpha} '
                               '\\left(\\cos\\alpha + '
                               '\\frac{\\sin\\alpha}{\\tan\\ang{20}}\\right)   '
                               '&=  0   \\nonumber\\\\\n'
                               '        &=  -\\sin\\alpha_{min} '
                               '+\\frac{\\cos\\alpha_{min}}{\\tan\\ang{20}}    '
                               '\\nonumber   \\\\\n'
                               '        \\tan\\alpha_{min}    &=  '
                               '\\frac{1}{\\tan\\ang{20}}  \\\\\n'
                               '        \\Rightarrow\\,\\alpha_{min} &= '
                               '\\ang{70} \\nonumber\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'Hence, $T_2$ is minimal when $T_2$ is '
                               'perpendicular to $T_1$.\n'
                               '\n',
                     'Text': 'the tension in each of the ropes, if $\\alpha = '
                             '\\ang{30}$.'},
                 {   'Answer': 'In order for the resultant force to be a force '
                               'with magnitude 30\xa0N oriented along the '
                               'horizontal, the following conditions must be '
                               'true,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_2 \\cos\\alpha + T_1 \\cos\\ang{20} &= '
                               '\\SI{30}{\\N}    \\\\\n'
                               '    T_2 \\sin\\alpha - T_1 \\sin\\ang{20} &= 0 '
                               '\\,.\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'Hence,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_2 &=  '
                               'T_1\\frac{\\sin\\ang{20}}{\\sin\\alpha}  \\\\\n'
                               '    \\left(  T_1 '
                               '\\frac{\\sin\\ang{20}}{\\sin\\alpha} \\right) '
                               '\\cos\\alpha &+ T_1\\cos\\ang{20} = '
                               '\\SI{30}{\\N} \\nonumber \\\\\n'
                               '    T_1 &=  '
                               '\\frac{\\SI{30}{\\N}}{\\frac{\\sin\\ang{20}}{\\tan\\alpha} '
                               '+ \\cos\\ang{20}}  \\,. \n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'When $\\alpha=\\ang{30}$, this yields\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_1&=\\SI{19.58}{\\N}\\\\\n'
                               '    T_2&=\\SI{13.39}{\\N}\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               '\n'
                               '\n'
                               'Substituting the expression for $T_1$, '
                               'equation\xa0, into the expression for $T_2$, '
                               'equation\xa0 allows us to determine $T_2$ as a '
                               'function of $\\alpha$,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    T_2 '
                               '&=\\frac{\\SI{30}{\\N}}{\\frac{\\sin\\ang{20}}{\\tan\\alpha} '
                               '+ \\cos\\ang{20}}    '
                               '\\frac{\\sin\\ang{20}}{\\sin\\alpha} '
                               '\\nonumber   \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}    '
                               '{\\sin\\ang{20}\\frac{\\cos\\alpha}{\\sin\\alpha} '
                               '+ \\cos\\ang{20}}  '
                               '\\frac{\\sin\\ang{20}}{\\sin\\alpha} '
                               '\\nonumber \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}    '
                               '{\\sin\\ang{20}\\frac{\\cos\\alpha}{\\sin\\alpha}\\frac{\\sin\\alpha}{\\sin\\ang{20}} '
                               '+ '
                               '\\cos\\ang{20}\\frac{\\sin\\alpha}{\\sin\\ang{20}}}    '
                               '\\nonumber \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}    '
                               '{\\cancel{\\sin\\ang{20}}  '
                               '\\frac{\\cos\\alpha}   '
                               '{\\cancel{\\sin\\alpha}}   '
                               '\\frac{\\cancel{\\sin\\alpha}}{\\cancel{\\sin\\ang{20}}} '
                               '+ '
                               '\\cos\\ang{20}\\frac{\\sin\\alpha}{\\sin\\ang{20}}}    '
                               '\\nonumber \\\\\n'
                               '        &=\\frac{\\SI{30}{\\N}}{\\cos\\alpha + '
                               '\\frac{\\sin\\alpha}{\\tan\\ang{20}}} \\,.\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'Examining the form of this, we can see that '
                               '$T_2$ will be minimal at $\\alpha_{min}$ when '
                               '$\\left(\\cos\\alpha + '
                               '\\frac{\\sin\\alpha}{\\tan\\ang{20}}\\right)$ '
                               'is maximal. Searching for maximal stationary '
                               'points in the usual manner,\n'
                               '\n'
                               '$$\n'
                               '\\begin{aligned}\n'
                               '    \\frac{\\mathrm{d}}{\\mathrm{d}\\alpha} '
                               '\\left(\\cos\\alpha + '
                               '\\frac{\\sin\\alpha}{\\tan\\ang{20}}\\right)   '
                               '&=  0   \\nonumber\\\\\n'
                               '        &=  -\\sin\\alpha_{min} '
                               '+\\frac{\\cos\\alpha_{min}}{\\tan\\ang{20}}    '
                               '\\nonumber   \\\\\n'
                               '        \\tan\\alpha_{min}    &=  '
                               '\\frac{1}{\\tan\\ang{20}}  \\\\\n'
                               '        \\Rightarrow\\,\\alpha_{min} &= '
                               '\\ang{70} \\nonumber\n'
                               '\\end{aligned}\n'
                               '\n'
                               '$$\n'
                               '\n'
                               'Hence, $T_2$ is minimal when $T_2$ is '
                               'perpendicular to $T_1$.\n'
                               '\n',
                     'Text': 'the value of $\\alpha$ such that the tension in '
                             'rope, $T_2$ is minimal.'}],
    'Title': ''}]
    
    with open("minimal_template.json", "r") as file:
        template = json.load(file)
    converter(template,ListQuestions)

if __name__ == '__main__':
    main()