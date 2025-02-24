import os
import dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate, FewShotChatMessagePromptTemplate


#from in2lambda.api.question import Question
from chains.llm_factory import LLMFactory

class Question:
    def __init__(self):
        pass


class QuestionConverter:
    def __init__(self):
        if not dotenv.load_dotenv():
            raise Exception('Error loading .env file')
        llm_factory_instance = LLMFactory()
        self.llm = llm_factory_instance.get_llm()


        self.examples = [
            {
                "input":
                    '''
                    A car is being towed with two ropes as shown in figure~\\ref{A1:fig:Q3}. If the resultant of the two forces is a \\SI{30}{\\N} force parallel to the long axis of the car, find:
                    \\begin{enumerate}
                        \\item the tension in each of the ropes, if $\\alpha = \\ang{30}$.
                        \\item the value of $\\alpha$ such that the tension in rope, $T_2$ is minimal.
                    \\end{enumerate}
                    \\begin{marginfigure}[-20mm]
                        \\centering
                        \\includegraphics[width=\columnwidth]{problem1_3.png}
                        \\caption{A car with two tow ropes attached.}
                        \\label{A1:fig:Q3}
                    \\end{marginfigure}
                    ''',
                "output":(
                    """
                    A car is being towed with two ropes as shown in figure~\\ref{A1:fig:Q3}. If the resultant of the two forces is a \\SI{30}{\\N} force parallel to the long axis of the car, find:
                    """,
                    [
                        """\\item the tension in each of the ropes, if $\\alpha = \\ang{30}$.""",
                        """\\item the value of $\\alpha$ such that the tension in rope, $T_2$ is minimal."""
                    ])
            },
            { 
                "input":
                    """A builder pulls with a force of \\SI{300}{\\N} on a rope attached to a building as shown in figure~\\ref{A1:fig:Q1a}. What are the horizontal and vertical components of the force exerted by the rope at the point A?
                    \\begin{figure}
                        \\centering
                        \\includegraphics[width=0.6\\columnwidth]{problem1_1a.png}
                        \\caption{A builder applying \\SI{300}{\\N} to a building using a rope.}
                        \\label{A1:fig:Q1a}
                    \\end{figure}""",
                "output":(
                    """A builder pulls with a force of \\SI{300}{\\N} on a rope attached to a building as shown in figure~\\ref{A1:fig:Q1a}. What are the horizontal and vertical components of the force exerted by the rope at the point A?""",
                    [],
                    )
            },
            {
                "input":"""Find the real and imaginary parts of:
                    $
                    \\begin{array}[h!]{lll}
                    {\\rm (a)}\\hskip5pt 8+3\\,i\\hskip24pt&
                    {\\rm (b)}\\hskip5pt 4-15\\,i\\hskip24pt&
                    {\\rm (c)}\\hskip5pt \\cos\\theta-i\\,\\sin\\theta\\\\
                    \\noalign{\\vskip12pt}
                    {\\rm (d)}\\hskip5pt i^2&
                    {\\rm (e)}\\hskip5pt i\\,(2-5\\,i)&
                    {\\rm (f)}\\hskip5pt (1+2\\,i)(2-3\\,i)
                    \\end{array}
                    $""",
                "output":(
                    """Find the real and imaginary parts of:""",
                    [
                        """{\\rm (a)}\\hskip5pt 8+3\\,i\\hskip24pt""",
                        """{\\rm (b)}\\hskip5pt 4-15\\,i\\hskip24pt""",
                        """{\\rm (c)}\\hskip5pt \\cos\theta-i\\,\\sin\\theta\\\\""",
                        """{\\rm (d)}\\hskip5pt i^2""",
                        """{\\rm (e)}\\hskip5pt i\\,(2-5\\,i)""",
                        """{\\rm (f)}\\hskip5pt (1+2\\,i)(2-3\\,i)"""
                    ])
            }
        ]


    def convert(self, question:str, solution:str) -> Question:
        '''
        Convert a question and solution to a Question object
        it's possible solution is a list of solutions or no solution at all
        '''

        # This is a prompt template used to format each individual example.
        example_prompt = ChatPromptTemplate.from_messages(
            [
                ("human", "{input}"),
                ("ai", "{output}"),
            ]
        )
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=self.examples,
        )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", """You are intelligent assistant to process the given input question, 
                            Please analyze the input question and respond with: 
                            1. Main Content (String).
                            2. Relevant parts (Comma and new line separated list).
                            Use format: "Main Content: <string>\\nParts: <Part1>, \\n<Part2>, \\n..."""),
                few_shot_prompt,
                ("human", "{input}"),
            ]
        )

        chain = final_prompt | self.llm

        print(question)
        result = chain.invoke({"input":question})
        print(result)
        return Question()
    
test_question = '''Write each of the following expressions as a complex number in the form $x+i\\,y$:
                    $
                    \\begin{array}[h!]{lll}
                    {\\rm (a)}\\hskip5pt (5-i)(2+3\\,i)\\hskip24pt&
                    {\\rm (b)}\\hskip5pt (3-4\\,i)(3+4\\,i)\\hskip24pt&
                    {\\rm (c)}\\hskip5pt (1+2\\,i)^2\\\\
                    \\noalign{\\vskip12pt}
                    {\\rm (d)}\\hskip5pt \\displaystyle{10\\over4-2\\,i}&
                    {\\rm (e)}\\hskip5pt \\displaystyle{3-i\\over4+3\\,i}&
                    {\\rm (f)}\\hskip5pt \\displaystyle{1\\over i}
                    \\end{array}
                    $'''
test_question2 = "Which city is the capital of China? \\item Beijing \\item Shanghai \\item Guangzhou"
test_converter = QuestionConverter()
test_converter.convert(test_question2, "")  
