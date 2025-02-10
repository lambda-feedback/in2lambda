# Requirements: langchain-openai langchain-community
#
# Usage: python3 high_level.py input.tex > output.tex
# It has been tested on two example files: 
# - problemsA_v2.7.tex
# - OandW_sample_PS1_Complete.tex (this is the concatenation of OandW_sample_PS1.tex and OandW_sample_PS1_Solutions.tex)

import getpass
import os
import json
import sys

from langchain_openai import AzureChatOpenAI
from langchain_community.callbacks import get_openai_callback

if "AZURE_OPENAI_API_KEY" not in os.environ:
    os.environ["AZURE_OPENAI_API_KEY"] = getpass.getpass(
        "Enter your AzureOpenAI API key: "
    )
if "AZURE_OPENAI_ENDPOINT" not in os.environ:
    os.environ["AZURE_OPENAI_ENDPOINT"] = getpass.getpass(
        "Enter the AzureOpenAI API endpoint: "
    )

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",
    api_version="2025-01-01-preview",  # or your api version
    temperature=0.5,
    max_tokens=None,
    timeout=None,
    max_retries=2
    # other params...
)

def extract_qa(text):
    # First approach with a single prompt (not used in this version)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        #{"role": "user", "content": f"Extract questions, answers, and solutions from the following text:\n\n{text}\n\nKeep math definitions verbatim\n\nFormat the output as JSON. The main JSON structure should be called 'questions'"}
        #{"role": "user", "content": f"Extract questions, answers, and solutions from the following text:\n\n{text}\n\nFormat the output as markdown files.\n\nKeep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block.\n\n"}
        #{"role": "user", "content": f"Extract questions, answers, and solutions as a triplet from the following text:\n\n{text}\n\nFormat the output as markdown files.\n\n- Identify and extract questions, answers, and solutions even if they are in different sections or files.\n- Handle subquestions like (a), (b), (c), etc., and group them under their main question.\n- If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.\n- Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.\n\nOutput format:\n\n## Question 1\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}\n\n## Question 2\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}\n\n..."}
        #{"role": "user", "content": f"Extract questions, answers, and solutions as a triplet from the following text:\n\n{text}\n\nFormat the output as markdown files.\n\n- Identify and extract questions, answers, and solutions even if they are in different sections or files.\n- Handle subquestions in various formats (e.g., (a), (b), (c), 1., 2., 3., *, *, *) and group them under their main question.\n- Ensure subquestions are correctly formatted in the Question, Answer, and Solution sections.\n- If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.\n- Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.\n\nOutput format:\n\n## Question 1\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}\n\n## Question 2\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}"}
        #{"role": "user", "content": f"Extract questions, answers, and solutions as a triplet from the following text:\n\n{text}\n\nFormat the output as markdown files.\n\n- Identify and extract questions, answers, and solutions even if they are in different sections or files.\n- Handle subquestions in various formats (e.g., (a), (b), (c), 1., 2., 3., *, *, *) and group them under their main question.\n- Ensure subquestions are correctly formatted in the Question, Answer, and Solution sections.\n- If a general solution applies to multiple subquestions, include it in the Solution section and indicate its applicability.\n- If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.\n- Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.\n\nOutput format:\n\n## Question 1\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}\n\n## Question 2\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}"}
        #{"role": "user", "content": f"Extract questions, answers, and solutions as a triplet from the following text:\n\n{text}\n\nFormat the output as markdown files.\n\n- Identify and extract questions, answers, and solutions even if they are in different sections or files.\n- Handle subquestions in various formats (e.g., (a), (b), (c), 1., 2., 3., *, *, *) and group them under their main question.\n- Ensure subquestions are correctly formatted in the Question, Answer, and Solution sections.\n- Extract the exact text for solutions, avoiding generalizations.\n- If a general solution applies to multiple subquestions, include it in the Solution section and indicate its applicability.\n- If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.\n- Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.\n\nOutput format:\n\n## Question 1\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}\n\n## Question 2\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}"}
        {"role": "user", "content": f"Extract questions, answers, and solutions as a triplet from the following text:\n\n{text}\n\nFormat the output as markdown files.\n\n- Identify and extract questions, answers, and solutions even if they are in different sections or files.\n- Handle subquestions in various formats (e.g., (a), (b), (c), 1., 2., 3., *, *, *) and group them under their main question.\n- Ensure subquestions are correctly formatted in the Question, Answer, and Solution sections.\n- Extract the exact text for answers and solutions, avoiding generalizations.\n- Clearly differentiate between answers and solutions, ensuring each is placed in the correct section.\n- If a general solution applies to multiple subquestions, include it in the Solution section and indicate its applicability.\n- If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.\n- Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.\n\nOutput format:\n\n## Question 1\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}\n\n## Question 2\n\n### Question\n\n{{question_text}}\n\n### Answer\n\n{{answer_text}}\n\n### Solution\n\n{{solution_text}}"}
    ]
    
    # Multi-prompt approach
    # Define the first prompt
    prompt1 = f"""
                Extract questions, answers, and solutions as a triplet from the following text:
                
                {text}
                
                Format the output as markdown files.
                
                - Identify and extract questions, answers, and solutions even if they are in different sections or files.
                - Handle subquestions in various formats (e.g., (a), (b), (c), 1., 2., 3., *, *, *) and group them under their main question.
                - Ensure subquestions are correctly formatted in the Question, Answer, and Solution sections.
                - Extract the exact text for answers and solutions, avoiding generalizations.
                - Clearly differentiate between answers and solutions, ensuring each is placed in the correct section.
                - If a general solution applies to multiple subquestions, include it in the Solution section and indicate its applicability.
                - If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.
                - Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.
                
                Output format:
                
                ## Question 1
                
                ### Question
                
                {{question_text}}
                
                ### Answer
                
                {{answer_text}}
                
                ### Solution
                
                {{solution_text}}
                
                ## Question 2
                
                ### Question
                
                {{question_text}}
                
                ### Answer
                
                {{answer_text}}
                
                ### Solution\n\n{{solution_text}}
                """

    with get_openai_callback() as cb:
        # Send the first prompt
        messages1 = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt1}
        ]
        response1 = llm.invoke(messages1)

        # Define the second prompt
        prompt2 = f"""
                    Based on the extracted information:
                    
                    {response1} verify that questions, answers, and solutions are triplets from the following text:
                    
                    {text}
                    
                    Check the output is formatted as markdown files.
                    
                    - Check the output is correctly identified and extract questions, answers, and solutions even if they are in different sections or files.
                    - Check that subquestions are handled in various formats (e.g., (a), (b), (c), 1., 2., 3., *, *, *) and grouped under their main question.
                    - Ensure subquestions are correctly formatted in the Question, Answer, and Solution sections.
                    - Extract the exact text for answers and solutions, avoiding generalizations.
                    - Clearly differentiate between answers and solutions, ensuring each is placed in the correct section.
                    - If a general solution applies to multiple subquestions, include it in the Solution section and indicate its applicability.
                    - If an answer or solution is missing, indicate it as 'Answer: Not provided' or 'Solution: Not provided'.
                    - Keep math syntax verbatim, surrounded by '$' symbols if inline or '$$' if block, keeping it to the very minimum.
                    
                    Avoid repetitions.
                    
                    Output format:
                    
                    ## Question 1
                     
                    ### Question
                    
                    {{question_text}}
                    
                    ### Answer
                    
                    {{answer_text}}
                    
                    ### Solution
                    
                    {{solution_text}}
                    
                    ## Question 2
                    
                    ### Question
                    
                    {{question_text}}
                    
                    ### Answer
                    
                    {{answer_text}}
                    
                    ### Solution
                    
                    {{solution_text}}
                    """

        # Send the second prompt
        messages2 = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt2}
        ]
        response2 = llm.invoke(messages2)

        #print(f"Total Cost (USD): ${format(cb.total_cost, '.6f')}")
    
    return response2.content.strip()

def process_file(file_path):
    with open(file_path, 'r') as file:
        text = file.read()
    return extract_qa(text)

# Get input file form command line argument (no checks on that)
file_path = sys.argv[1]
qa_md = process_file(file_path)
print(qa_md)
