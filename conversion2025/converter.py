#!/usr/bin/env python
# coding: utf-8

# # process description  
# 
# the program takes in a pdf  
# mathpix is used to scan the pdf and turning it into markdown  
# markdown then processed to get the images  
# 
# llm is used to extract the questions and solutions in **ONE** go.  
# the final JSON is made using the in2lambda api.

# In[1]:


import os
import re
import json
import time
import requests
import concurrent.futures

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import pypandoc

from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser

from in2lambda.api.set import Set
from in2lambda.api.question import Question
from in2lambda.api.part import Part

from PIL import Image

# Load environment variables from .env file.
load_dotenv()


# # scanning/processing the initial pdf into markdown

# In[2]:


MATHPIX_API_KEY = os.getenv("MATHPIX_API_KEY")
MATHPIX_APP_ID = os.getenv("MATHPIX_APP_ID")

def pdf_to_markdown(source_path: str, result_path: str):
    ''' 
    converts the pdf at `source_path` to a markdown file at `result_path` using Mathpix API.
    '''
    # Upload PDF to Mathpix and returns a Markdown file with the content.
    with open(source_path, "rb") as file:
        r = requests.post(
            "https://api.mathpix.com/v3/pdf",   
            headers={
                "app_id": MATHPIX_APP_ID,
                "app_key": MATHPIX_API_KEY,
            },
            files={"file": file},
        )
        pdf_id = r.json()["pdf_id"]
        print("PDF ID:", pdf_id)
        print("Response:", r.json())

        # url of where the location of the processed PDF will be
        url = f"https://api.mathpix.com/v3/pdf/{pdf_id}.md"
        headers = {
            "app_id": MATHPIX_APP_ID,
            "app_key": MATHPIX_API_KEY,
        }

        max_retries = 10
        retry_delay = 5  # seconds
        for attempt in range(max_retries):
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                # Save the result if the request is successful
                with open(result_path, "w") as f:
                    f.write(response.text)
                print("Downloaded MD successfully.")
                break
            else:
                print(f"Attempt {attempt + 1}/{max_retries}: Processing not complete. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        else:
            print("Failed to retrieve processed PDF after multiple attempts:", response.status_code, response.text)


# # setting up the directories

# In[ ]:


# location of the output folder and media folder.
folder_path = "conversion_content"
input_path = f"{folder_path}/input"
output_path = f"{folder_path}/converter"
media_path = f"{output_path}/media"

# Create output and media directories if they do not exist.
Path(media_path).mkdir(parents=True, exist_ok=True)

# location of the source pdf file and the result markdown file.
files = [f for f in os.listdir(input_path) if f != '.gitkeep']
source_path = f"{input_path}/{files[0]}" # the first file in the input folder
result_path = f"{output_path}/example.md"



# Only activate mathpix if the markdown has not been created yet.
# This avoids unnecessary reprocessing of the same PDF.
if not Path(result_path).exists():
    if Path(source_path).exists():
        extension = Path(source_path).suffix.lower() # obtains the file extension
        if extension == ".pdf":
            pdf_to_markdown(source_path, result_path)
        else:
            pypandoc.convert_file(source_path, 'md', outputfile=result_path)
    else:
        print(f"Error: Source PDF file not found at {source_path}")
        exit(1)

# Read the markdown content from the result file.
try:
    with open(result_path, "r") as f:
        md_content = f.read()
except FileNotFoundError:
    print(f"Error: Markdown file not found at {result_path}")
    exit(1)

# Print out a summary.
print("Markdown text: ")
print(f"  {result_path}: {len(md_content)} characters")
print("Markdown text: ")
print(f"  {result_path}: {md_content}")


# # downlaoding extracted images from Mathpix

# In[4]:


# Fetch the figures from the paper and answers.
def extract_figures_from_text(text): #, ans=False):
    """
    Extracts figures from the text using regex.
    Finds figure references and their descriptions.
    """
    figures = {}
    # Regex to match figure references and their descriptions
    # Matches ![alt text](url) format for images
    pattern = r'!\[.*?\]\((.*?)\)'
    matches = re.findall(pattern, text)
    print(f"Matches found: {matches}")
    
    for match in matches:
        url = match
        url = url.strip()
        
        if url.startswith("http"):
            # Download the image and save it to a file
            image = Image.open(requests.get(url, stream=True).raw)
            # Create a figure name based on the URL
            fig_name = os.path.basename(url)
            figures[fig_name] = {
                "image": image,
                "url": url,
                "local_path": "",
                # "answerFile": ans
            }
    return figures

# a dictionary storing information on the figures
figures = extract_figures_from_text(md_content)


# # saving the images locally

# In[5]:


def save_figures_to_path(figures):
    for idx, (fig_name, fig_info) in enumerate(figures.items()):
        print(f"URL='{fig_info['url']}'")

        # Extract file extension and create a clean filename
        # Mathpix leaves image urls like `image.png?width=800&height=600`
        # We only want the base name without query parameters.
        if "?" in fig_name:
            end_location = fig_name.index("?")
            image_name = f"{idx}_{fig_name[:end_location]}"
        else:
            image_name = f"{idx}_{fig_name}"
        
        fig_info["local_path"] = image_name
        try:
            # Saves the image to the media path
            fig_info["image"].save(f"{media_path}/{fig_info['local_path']}")
            print(f"Saved image: {fig_info['local_path']}")
        except Exception as e:
            print(f"Error saving image {image_name}: {e}")

save_figures_to_path(figures)


# # replacing url for images with local path

# In[6]:


def replace_figures_in_markdown(md_content, figures) -> str:
    #replace the image URLs in the markdown content with local paths
    # add pictureTag for Lambda Feedback to recognise it as a picture
    md_content = md_content.replace("![]", "![pictureTag]")
    for fig_name, fig_info in figures.items():
        md_content = md_content.replace(fig_info["url"], fig_info["local_path"])
        print(f"Replaced {fig_info['url']} with {fig_info['local_path']} in markdown content.")
    # Save the modified markdown content to a file
    try:
        with open(f"{output_path}/example.md", "w") as f:
            f.write(md_content)
        print("Modified markdown saved successfully.")
    except Exception as e:
        print(f"Error saving modified markdown: {e}")
    
    return md_content

md_content = replace_figures_in_markdown(md_content, figures)


# # Initialising llm

# In[7]:


# Set up the LLM via LangChain.

# Uses gpt-4.1-nano:
#    - a faster model
#    - less intelligent

llm_nano = ChatOpenAI(
            model="gpt-4.1-nano",
            api_key=os.environ["OPENAI_API_KEY"],
        )

# Uses gpt-5-mini:
#    - more intelligent
llm_mini = ChatOpenAI(
            model="gpt-5-mini",
            api_key=os.environ["OPENAI_API_KEY"],
            reasoning_effort="medium",
            service_tier = "priority"
        )


# # Spelling and structure check (unused)

# In[8]:


llm_task_correct_mistakes = """
The input is a markdown file that is converted from a pdf using Mathpix API.
The pdf contains questions and may contain the solutions too.
As the original pdf may contain hand written text, the markdown file may contain mistakes in spelling, grammar and structure.

Important things to remember:
    1. Leave all Math commands and LaTeX formatting the same. As they are completely valid. Do not change the LaTeX formatting and expressions.
    2. Only ever use LaTeX math delimiters for math expressions. I.e. use `$...$` for inline math, and `$$...$$` for display math.
    3. Leave references to images and figures the same. I.e. do not change the image links or alt text.

Your task is to:
    1. Correct any spelling mistakes in the markdown file.
    2. Correct any grammar mistakes in the markdown file.
    3. Correct any layout mistakes in the markdown file, such that it follows the styles of the entire markdown file.
    4. Do not change the content of the markdown file, only correct the mistakes.
Output only a valid markdown file with the corrections applied, if any. Do not add any additional text or comments.
"""

def correct_mistakes_in_markdown(md_content: str) -> str:
    correct_mistakes_prompt = f"""
        {llm_task_correct_mistakes}

        ```input
        {md_content}
        ```

        Return the markdown now.
    """

    response = llm_nano.invoke(correct_mistakes_prompt)
    print("Corrected markdown content:")
    print(response.content.strip())

    return response.content.strip()


# # Transform into markdown

# In[9]:


# intermediate representation of the markdown
class Markdown():
    def __init__(self, content):
        self.content = content

class InlineMath(Markdown):
    def __init__(self, content):
        super().__init__(content)
        self.delimiter_size = 2

    def __str__(self):
        return f"InlineMath({self.content!r})"
    
    def __repr__(self):
        return f"InlineMath({self.content!r})"
    

class DisplayMath(Markdown):    
    def __init__(self, content):
        super().__init__(content)
        self.delimiter_size = 4

    def __str__(self):
        return f"DisplayMath({self.content!r})"
    
    def __repr__(self):
        return f"DisplayMath({self.content!r})"

class RegularText(Markdown):
    def __init__(self, content):
        super().__init__(content)

    def __str__(self):
        return f"RegularText({self.content!r})"

    def __repr__(self):
        return f"RegularText({self.content!r})"

# Functions to convert between markdown text and the intermediate representation by lines.
def convert_markdown_to_classes_by_lines(markdown: str) -> list[Markdown]:
    lines = markdown.split("\n")
    ret = []
    math_buffer = []
    displayMath = False
    for line in lines:
        if line == "$$":
            displayMath = not displayMath
            if not displayMath:
                ret.append(DisplayMath("\n".join(math_buffer)))
                math_buffer = []
        else:
            if displayMath:
                math_buffer.append(line)
            else:
                ret.append(RegularText(line))
    return ret

def convert_classes_to_markdown_by_lines(classes: list[Markdown]) -> str:
    lines = []
    for c in classes:
        match c:
            case InlineMath():
                lines.append(f"${c.content}$")
            case DisplayMath():
                lines.append(f"$$\n{c.content}\n$$")
            case RegularText():
                lines.append(c.content)
    return "\n".join(lines)


# Functions to convert between markdown text and the intermediate representation.

def convert_markdown_to_classes(md_content: str) -> list[Markdown]:
    index = 0
    classes = []

    while index < len(md_content):
        # no need to check index range since there is always at least 2 characters left
        if md_content[index: index+2] == "$$":
            display_math = []
            index += 2
            while index < len(md_content)-1 and md_content[index: index+2] != "$$":
                display_math.append(md_content[index])
                index += 1
            classes.append(DisplayMath("".join(display_math)))
            index += 2
        
        elif md_content[index] == "$":
            inline_math = []
            index += 1
            while index < len(md_content) and md_content[index] != "$":
                inline_math.append(md_content[index])
                index += 1
            classes.append(InlineMath("".join(inline_math)))
            index += 1

        else:
            regular_text = []
            while index < len(md_content) and md_content[index] != "$":
                regular_text.append(md_content[index])
                index += 1
            classes.append(RegularText("".join(regular_text)))

    return classes

def convert_classes_to_markdown(classes: list[Markdown]) -> str:
    md_content = []
    for c in classes:
        match c:
            case InlineMath():
                md_content.append(f"${c.content}$")
            case DisplayMath():
                md_content.append(f"$${c.content}$$")
            case RegularText():
                md_content.append(c.content)
    return "".join(md_content)


# # Extract Questions

# In[10]:


#define initial question model
class QuestionModelLines(BaseModel):
    # full question and full solution
    question_content_start: int = Field(..., description="Line number the question starts on.")
    question_content_end: int = Field(..., description="Line number the question ends on.")
    solution_content_start: int = Field(..., description="Line number the solution starts on.")
    solution_content_end: int = Field(..., description="Line number the solution ends on.")

class AllQuestionsModelLines(BaseModel):
    name: str = Field(..., description="Title of the set")
    year: str = Field(..., description="Year of the set")
    questions: list[QuestionModelLines] = Field(..., description="A list of questions.")

llm_task_seperate_questions = """
    Think very carefully before outputting.
    Your task is to extract the line numbers for the start and end of all the question and solution from the markdown file, then format it as a JSON object.
    Note that the questions and solutions may not be around the same area in the markdown file.
    These line numbers will be used later to extract the content of the questions and solutions procedurally.
    
    1.  **Content Extraction:**
        -   Your may choose a suitable name for the set of questions.
        -   Identify the `year` of the questions, otherwise use "0".
        -   Begin by identifying all the distinct individual full questions in the markdown file, which are likely explicitly enumerated, and for each question:
            -   Identify the start and end line numbers of the full question content, and place them in `question_content_start` and `question_content_end`.
            -   Identify the start and end line numbers of the full relevant solution content, and place them in `solution_content_start` and `solution_content_end`.
            -   Be careful to ensure that everything related to the question and solution is included, including any math delimiters($, $$) and LaTeX formatting.
            -   Do not forget to include any images or figures that are part of the question or solution.
    
    2.  **Output Format:**
        -   You MUST output ONLY a single, raw, valid JSON string that matches the provided schema.
        -   Do NOT include any explanations, comments, or markdown code blocks (like ```json).
    """

example_seperate_questions = """
    Example input:
    [(0, "Q1: Give a fruit begining with these letters:"),
    (1, "a) a"),
    (2, "b) b"),
    (3, "c) c"),
    (4, "Q2: What is the capital of France?"),
    (5, "Q3: What is the colour of the sky?"),
    (6, "A1:"),
    (7, "a) = apple"),
    (8, "b) = banana"),
    (9, "c) = cherry"),
    (10, "A2: Paris is the capital of France."),
    (11, "A3: The sky is blue.")
    ]

    example output:
    {
        "name": "Suitable Name",
        "year": "0",
        "questions": [
            {
                "question_content_start": 0,
                "question_content_end": 3,
                "solution_content_start": 5,
                "solution_content_end": 8
            },
            {
                "question_content_start": 4,
                "question_content_end": 4,
                "solution_content_start": 9,
                "solution_content_end": 9
            },
            {
                "question_content_start": 5,
                "question_content_end": 5,
                "solution_content_start": 10,
                "solution_content_end": 10
            },
            {
                "question_content_start": 6,
                "question_content_end": 6,
                "solution_content_start": 11,
                "solution_content_end": 11
            }
        ]
    }
    """

# Prompt for the LLM to extract questions.
def seperate_questions_prompt(parser: PydanticOutputParser[AllQuestionsModelLines], doc_page_content: list[Markdown]) -> str: #, previous_repsonse: str = "", improvements: list[str] = "") -> str:

    feedback = ""
    # if previous_repsonse:
    #     feedback = f"""
        
    #         Previous output:
    #         {previous_repsonse}

    #         Improvements:
    #         {improvements}

    #     """

    return f"""
        Your task is to extract a JSON with the following structure exactly, ready to be parsed by a pydantic model:
        {parser.get_format_instructions()}

        {llm_task_seperate_questions}

        {example_seperate_questions}

        Input markdown:
        ```
        {list(enumerate(doc_page_content))}
        ```
        {feedback}
        Return the JSON now.
    """


# # extracting images from content

# In[11]:


def extract_images(text: str) -> list[str]:
    """
    Extracts image URLs from the markdown text.
    Returns a list of image URLs.
    """
    pattern = r'!\[.*?\]\((.*?)\)'
    matches = re.findall(pattern, text)
    return matches


# # extracting questions form the problem sheet

# In[12]:


class QuestionModel(BaseModel):
    # full question and full solution
    question_content: str = Field(..., description="The content of the question.")
    solution_content: str = Field(..., description="The content of the solution.")
    images: list[str] = Field(..., description="A list of image URLs associated with the question.")

class AllQuestionsModel(BaseModel):
    name: str = Field(..., description="Title of the set")
    year: str = Field(..., description="Year of the set")
    questions: list[QuestionModel] = Field(..., description="A list of questions.")


def extract_questions(allQuestionsModel: AllQuestionsModelLines, doc_page_content: list[Markdown]) -> AllQuestionsModel:
    """
    Extracts questions from the AllQuestions model and returns a list of Question objects.
    """
    print("Extracting questions from the AllQuestions model...")

    name = allQuestionsModel.name
    year = allQuestionsModel.year
    questions = []

    for question in allQuestionsModel.questions:
        question_content = convert_classes_to_markdown_by_lines(doc_page_content[question.question_content_start:question.question_content_end+1])
        solution_content = convert_classes_to_markdown_by_lines(doc_page_content[question.solution_content_start:question.solution_content_end+1])
        #important, image will be wrong if two identical images are used, although this should not be possible.
        images = list(set(extract_images(question_content) + extract_images(solution_content)))

        questions.append(
            QuestionModel(
                question_content=question_content,
                solution_content=solution_content,
                images=images
            )
        )
    
    allQuestions = AllQuestionsModel(
        name=name,
        year=year,
        questions=questions
    )
    
    print(f"Extracted {len(questions)} questions from the AllQuestions model.")
    return allQuestions


# In[13]:


class QuestionSeperationEvaluation(BaseModel):
    well_separated: bool = Field(..., description="Whether the question was separated well.")
    improvements: list[str] = Field(..., description="List of improvements to be made to the question separation.")

def evaluate_questions_separation(parsed_output: AllQuestionsModel, markdown: list[str]) -> list[QuestionSeperationEvaluation]:
    print("begin evaluation of llm output for question separation...")

    def evaluate_single_question_separation(question: QuestionModel) -> QuestionSeperationEvaluation:

        parser = PydanticOutputParser(pydantic_object=QuestionSeperationEvaluation)
        
        llm_task_evaluate_question_separation = f"""
        Your task is to evaluate the question separation of the following question.
        After evaluating the question separation, return a JSON object with the following structure:
        {parser.get_format_instructions()}

        Earlier, an llm was used to separate a markdown file into questions and its relavant solution by returning the lines where the question and solution start and end.
        This is to ensure that the math delimiters and laTeX formatting is preserved, since the original markdown has perfect formatting and structure.
        However, as with any LLM, it may not have returned the best lines for this particular question.
        Evaluate this one singular full question, which has been procedurally extracted from the markdown file using the lines given by the llm.
        Using the full markdown, check if the question was extracted correctly (note that the question and its solution may not be in the same area), in particular, check that:
            -  There is only 1 full question per `question_content`.
            -  The full question content from the markdown is included, which may contain its sub-questions and parts, which is fine as it will be separated later.
            -  The full solution content from the markdown is included, which should include the full solution for the question and its parts.
            -  The question and solution Text should have its math delimiters($, $$) and LaTeX formatting preserved and well closed.
            -  Ignore all typos and grammar mistakes, since they are not relevant to the question separation.
            -  only comment on things that can be improved.
        Be Very precise with what you believe is wrong, if any.
        If you believe the question was separated fairly well, set `well_separated` to true and leave `improvements` empty.
        If you believe the question was not separated correctly, set `well_separated` to false and provide a list of precise, improvements to be made.

        example input #1 valid questions:
        {{
            "question_content": "1. Give a fruit beginning with these letters: a) A, b) B, c) C",
            "solution_content": "1. a) = apple, b) = banana, c) = cherry",
            "images": []
        }}
        example output #2 well separated response:
        {{
            "well_separated": True,
            "improvements": []
        }}

        example input #2 invalid questions:
        {{
            "question_content": "3. Give the capital of France? \n 4. What is the colour of the sky?",
            "solution_content": "3. Paris, 4. Blue",
            "images": []
        }}
        example output #2 not well separated response:
        {{
            "well_separated": False,
            "improvements": [
                "Two full questions were found in the question content.",
                "Two full solutions were found in the solution content.",
            ]
        }}

        example input #3 invalid questions:
        {{
            "question_content": "Q1: solve for x: 2x + 3 = 7",
            "solution_content": "\\begin{{aligned}} 2x + 3 &= 7 \\\\ 2x &= 4 \\\\ x &= 2 \end{{aligned}}",
            "images": []
        }} 
        example output #3 not well separated response:
        {{
            "well_separated": False,
            "improvements": [
                "Missing opening and closing math delimiters around the LaTeX solution display math.",
            ]
        }}

        full markdown:
        {markdown}

        extracted question:
        {question}

        return the JSON now.
        """

        for attempt_idx in range(3):
            try:
                response = llm_nano.invoke(llm_task_evaluate_question_separation)
                parsed_response = parser.parse(response.content)
                return parsed_response
            except:
                print(f"Evaluation parse error on attempt {attempt_idx + 1}")
                time.sleep(2)

        else:
            raise Exception("Failed to evaluate question separation after 3 attempts.")

    # Use ThreadPoolExecutor to evaluate each question in parallel.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        questions_in_parts = list(executor.map(evaluate_single_question_separation, parsed_output.questions))

    print("Evaluated all questions for separation.")
    return questions_in_parts
    


# In[14]:


def llm_extract_questions_lines(markdown: list[Markdown]) -> AllQuestionsModel:
    print("Begining to seperate the questions from the markdown content...")
    
    # Initialise the parser for the output.
    parser = PydanticOutputParser(pydantic_object=AllQuestionsModelLines)

    previous_response = ""
    improvements = []

    for attempt_idx in range(3):
        try:
            response = llm_mini.invoke(seperate_questions_prompt(parser, markdown)) #, previous_response, improvements))
            parsed_response = parser.parse(response.content)
            questions_dict = extract_questions(parsed_response, markdown)
            print(questions_dict.model_dump_json())

            # evaluation = evaluate_questions_separation(parsed_output=questions_dict, markdown=markdown)
            # if all(e.well_separated for e in evaluation):
            if True:
                print("Question separation was successful.")
                return questions_dict
            else:
                previous_response = parsed_response.model_dump_json()
                improvements = [f"question {i + 1} improvements:{evaluation[i].improvements}" for i in range(len(evaluation)) if not evaluation[i].well_separated]
                print(f"Evaluation failed. trying again... {improvements}")
        except:
            print(f"Parse error on attempt {attempt_idx + 1}")
    else:
        raise Exception("Failed to extract questions after 3 attempts.")


# # Extract question parts and solutions

# In[15]:


# Define the schema for the tutorial output.
class Set_Question_Part_Lines(BaseModel):
    """
    Represents a part of a question with its start and end lines.
    """
    part_start: int = Field(..., description="The start line number of the part.")
    part_end: int = Field(..., description="The end line number of the part.")
    
class Set_Question_Lines(BaseModel):
    title: str = Field(..., description="Title of the question (only the text, no numbering)")
    content_start: int = Field(..., description="start of the content of the question (no exercise title, no subquestions)")
    content_end: int = Field(..., description="end of the content of the question (no exercise title, no subquestions)")
    parts: list[Set_Question_Part_Lines] = Field(..., description="List of parts within the question (only the text, no numbering)")

class Set_Question(BaseModel):
    title: str = Field(..., description="Title of the question (only the text, no numbering)")
    content: str = Field(..., description="Content of the question (no exercise title, no subquestions)")
    parts: list[str] = Field(..., description="List of parts within the question (only the text, no numbering)")
    images: list[str] = Field(..., description="List of image URLs associated with the question (no alt text, only URLs)")


class Set_Solution_Part_Lines(BaseModel):
    part_solution_start: int = Field(..., description="The start of the worked solution for the part (no numbering or counting)")
    part_solution_end: int = Field(..., description="The end of the worked solution for the part (no numbering or counting)")

class Set_Solution(BaseModel):
    parts_solutions: list[str] = Field(..., description="List of worked solutions for the question (no numbering or counting)")


class Set_Question_With_Solution(Set_Question):
    parts_solutions: list[str] = Field(..., description="The worked solution for the parts.")

    def __init__(self, question: Set_Question, solution: Set_Solution):
        """
        Initialize the Set_Question_With_Solution with a question and its solution.
        
        Args: 
            question (Set_Question): The question object.
            solution (Set_Solution): The solution object.
        """
        super().__init__(
            **question.model_dump(),
            parts_solutions=solution.parts_solutions,
        )


class Set_Lines(BaseModel):
    name: str = Field(..., description="Title of the set")
    year: str = Field(..., description="Year of the set")
    questions: list[Set_Question_With_Solution] = Field(..., description="List of questions in the set")

llm_task_seperate_parts_question = r"""
    1. **Content Extraction:**
        -   You may choose the `title` for the question.
        -   From the input `Full Question Content`, identify the start line and end line for the main introductory text (the stem), place them in `content_start` and `content_end`.
        -   From the input `Full Question Content`, identify and separate all the `parts`(sub-questions), sub-questions should be able to be identified explicitly (e.g. using, "(a)", "(b)", "i.", "ii."... etc.). For each identified sub-question:
            -   Place the start line going into `part_start` and the end line going into `part_end`.
            -   If the question has no sub-questions, leave `part_start` as 0 and `part_end` as -1.
            -   You may use the `Full Solution Content` to help with identifying the parts.
        -   Be careful to ensure that everything related to the question stem/parts is included, including any math delimiters($, $$) and LaTeX formatting.
        -   Do not forget to include any images or figures that are part of the question stem, parts or solution.
        -   Ensure no solution content is included in the `content` or `parts` fields.
    
    2.  **Output Format:**
        -   You MUST output ONLY a single, raw, valid JSON string that matches the provided schema.
        -   Do NOT include any explanations, comments, or markdown code blocks (like ```json).
    """

example_seperate_parts_question = r"""
    example:
    [(0, "Q1. find value of $x$ in the following equation:"),
    (1, "i. $x + 1 = 2$"),
    (2, "ii. $x - 1 = 5$")]

    should be converted to:
    {
        "title": "suitable title",
        "content_start": 0,
        "content_end": 0,
        "parts": [
            {
                "part_start": 1,
                "part_end": 1
            },
            {
                "part_start": 2,
                "part_end": 2
            }
        ]
    }
    """

llm_task_seperate_parts_solution = r"""
    1. **Content Extraction:**
        -   From the input `full solution content`, identify the specific solution part that corresponds to the `target question part`, and place the start line and end line into `part_solution_start` and `part_solution_end`.
        -   If the `target question part` is empty, identify the specific solution part that corresponds to the `full question stem`.
        -   Use the `full question stem` and `full question parts` to help identify the specific solution part.
        -   Ensure that the `target question part` is used to extract the specific solution part.
        -   Be careful to ensure that everything related to the solution part is included, including any math delimiters($, $$) and LaTeX formatting.
        -   Do not forget to include any images or figures that are part of the solution.

    2.  **Output Format:**
        -   You MUST output ONLY a single, raw, valid JSON string that matches the provided schema.
        -   Do NOT include any explanations, comments, or markdown code blocks (like ```json).
    """


# In[16]:


def convert_set_question_lines_to_set_question(set_question_lines: Set_Question_Lines, question_content: list[Markdown], images: list[str] = []) -> Set_Question:
    """
    Convert Set_Question_Lines to Set_Question.
    """
    return Set_Question(
        title=set_question_lines.title,
        content=convert_classes_to_markdown_by_lines(question_content[set_question_lines.content_start:set_question_lines.content_end + 1]),
        parts=[convert_classes_to_markdown_by_lines(question_content[part.part_start:part.part_end + 1]) for part in set_question_lines.parts],
        images=images
    )

def convert_set_solution_lines_to_set_solution(set_solution_lines: list[Set_Solution_Part_Lines], solution_content: list[Markdown]) -> Set_Solution:
    """
    Convert Set_Solution_Part_Lines to Set_Solution.
    """
    return Set_Solution(
        parts_solutions=[
            convert_classes_to_markdown_by_lines(solution_content[part.part_solution_start:part.part_solution_end + 1])
            for part in set_solution_lines
        ]
    )


# In[17]:


def process_single_question(question_data: tuple[int, QuestionModel]) -> Set_Question_With_Solution:
    """Process a single question and its parts in parallel"""
    question_idx, question = question_data
    
    # Initialize the output parser with the Set_Question schema.
    question_parser = PydanticOutputParser(pydantic_object=Set_Question_Lines)

    question_input: list[Markdown] = convert_markdown_to_classes_by_lines(question.question_content)
    solution_input: str = question.solution_content
    all_images = question.images

    # Prompt for the LLM to extract The question parts.
    # Use the full question content and the images to extract the parts.
    seperate_parts_question_prompt = f"""
        Your task is to extract a JSON with the following structure exactly, ready to be parsed by a pydantic model:
        {question_parser.get_format_instructions()}

        {llm_task_seperate_parts_question}

        {example_seperate_parts_question}

        Full Solution Content:
        {solution_input}

        Full Question Content:
        {list(enumerate(question_input))}

        Return the JSON now.
        """
    
    # Process the question part
    for attempt_idx in range(3):

        response = llm_mini.invoke(seperate_parts_question_prompt)

        try:
            parsed_output_parts = question_parser.parse(response.content)
            if len(parsed_output_parts.parts) < 1:
                raise Exception("all questions should have at least 1 part.")
            print(f"LLM response successfully parsed question {question_idx + 1}.")
            break
        except Exception as e:
            print(f"Error parsing LLM response as JSON for question {question_idx + 1}:")
            print(f"Retrying... Attempt No.{attempt_idx + 1}")
            time.sleep(2)
    else:
        print("Final LLM Response:")
        print(response.content)
        raise Exception(f"Failed to parse LLM response as JSON after multiple attempts for question {question_idx + 1}.")

    # Convert from Set_Question_Lines to Set_Question
    parsed_output_parts = convert_set_question_lines_to_set_question(parsed_output_parts, question_input, all_images)

    # Process solution parts in parallel
    def process_solution_part(part_data) -> Set_Solution_Part_Lines:
        part_idx, part = part_data
        solution_parser = PydanticOutputParser(pydantic_object=Set_Solution_Part_Lines)

        target_solution_input: list[Markdown] = convert_markdown_to_classes_by_lines(solution_input)

        # Prompt for the LLM to extract The solution part.
        # Use the full solution content and the part to extract the specific solution.
        seperate_parts_solution_prompt = f"""
            Your task is to extract a JSON with the following structure exactly, ready to be parsed by a pydantic model:
            {solution_parser.get_format_instructions()}

            {llm_task_seperate_parts_solution}

            full question stem:
            {parsed_output_parts.content}

            full question parts:
            {parsed_output_parts.parts}
            
            full solution content:
            {list(enumerate(target_solution_input))}

            target question part:
            {part}
            """
            
        for attempt_idx in range(3):
            
            response = llm_mini.invoke(seperate_parts_solution_prompt)
            
            try:
                parsed_output_solution_part = solution_parser.parse(response.content)
                print(f"LLM response successfully parsed solution for part {part_idx + 1} of question {question_idx + 1}.")
                return parsed_output_solution_part
            except Exception as e:
                print(f"Error parsing LLM response as JSON for part {part_idx + 1} of question {question_idx + 1}:")
                print(f"Retrying... Attempt No.{attempt_idx + 1}")
                time.sleep(2)
        
        else:
            print("Final LLM Response:")
            print(response.content)
            raise Exception(f"Failed to parse LLM response as JSON after multiple attempts part {part_idx + 1} of question {question_idx + 1}:")

    # Process all parts in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        part_data_list = [(i, part) for i, part in enumerate(parsed_output_parts.parts)]
        solutions_parts = list(executor.map(process_solution_part, part_data_list))

    solutions_parts = convert_set_solution_lines_to_set_solution(
        solutions_parts, 
        convert_markdown_to_classes_by_lines(solution_input)
    )

    # set_solution = Set_Solution(parts_solutions=solutions_parts)
    return Set_Question_With_Solution(
        question=parsed_output_parts,
        solution=solutions_parts
    )

def extract_parts_question(questions_dict: AllQuestionsModel) -> Set_Lines:
    """
    Extracts the title and individual questions from a tutorial sheet.
    Now processes questions in parallel while maintaining order.
    """
    print("Extracting parts from the questions...")

    # Process all questions in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        question_data_list = [(i, q) for i, q in enumerate(questions_dict.questions)]
        questions_in_parts = list(executor.map(process_single_question, question_data_list))
    
    print("Successfully extracted parts from all questions.")
    return Set_Lines(
        name=questions_dict.name,
        year=questions_dict.year,
        questions=questions_in_parts
    )


# # remove the duplicated text for single part questions

# In[18]:


# class NoPartsQuestionModel(BaseModel):
#     """
#     Represents a question without parts.
#     """
#     hasParts: bool = Field(False, description="Indicates if the question has parts.")

# llm_task_remove_dupe = """
#     1.  **Task:**
#         -   Check if the single part that the question has is the same as the full question content.
#         -   If it is not, then remove the part and set `hasParts` to `False`.
#         -   If it is, then set `hasParts` to `True`.
        
#     2.  **Output Format:**
#         -   You MUST output ONLY a single, raw, valid JSON string that matches the provided schema.
#         -   Do NOT include any explanations, comments, or markdown code blocks (like ```json).
#     """
# def llm_remove_dupe_part(content: str, part: str) -> bool:
#     return content == part

def dupe_text_reduce(questions_dict: Set_Lines) -> Set_Lines:
    """
    Reduces duplicate text in the questions content and its parts.
    """
    for question in questions_dict.questions:
        parts = question.parts
        if len(parts) == 1 and parts[0] == question.content:
            # If the only part is the same as the content, remove the part and set hasParts to False.
            question.parts[0] = ""
    
    return questions_dict


# # trim unwanted text

# In[19]:


# the position of the start and end of the trim may miss out on delimiters.
# but overall the position should be fairly accurate.

def improve_trim(text: str, start: int, end: int) -> str:
    markdown_classes = convert_markdown_to_classes(text)
    # print(markdown_classes)
    text_index = 0
    class_index = 0
    improved_start = -1
    improved_end   = -1

    while class_index < len(markdown_classes):
        structure = markdown_classes[class_index]

        match structure:
            case RegularText():
                structure_length = len(structure.content)
                temp_improved_start = 0
                temp_improved_end = len(structure.content)
                if text_index <= start and structure_length + text_index > start:
                    improved_start = class_index
                    temp_improved_start = start - text_index

                if text_index <= end and structure_length + text_index >= end:
                    improved_end = class_index
                    temp_improved_end = end - text_index
                
                structure.content = structure.content[temp_improved_start:temp_improved_end]
                text_index += structure_length

            case InlineMath() | DisplayMath():
                structure_length = len(structure.content) + structure.delimiter_size
                if text_index <= start and structure_length + text_index > start:
                    improved_start = class_index
                if text_index <= end and structure_length + text_index >= end:
                    improved_end = class_index
                text_index += structure_length
                
        class_index += 1


    ret = markdown_classes[improved_start:improved_end + 1]
    # print(ret)
    # print(len(text), start, end)
    # print(improved_start, improved_end)

    return convert_classes_to_markdown(ret)



# In[20]:


class TrimPosition(BaseModel):
    start: str = Field(..., description="The start position of the trim.")
    end: str = Field(..., description="The end position of the trim.")

llm_task_trim_content = f"""
    You will be given the full text of a question, extracted from a markdown file using line numbers.
    Assuming the extracted text is correct, then only the start of the first and the end of last lines may contain unwanted text.
    The first and last lines may contain unwanted text, such as:
        - Question numbering (e.g. "1.", "2.", "(a)", "(b)", "i.", "ii.", etc.)
        - Text from the previous or next question.
    We want to remove this unwanted text.

    Focus only on the actual stem (content) of the question.

    Your task is to, using the full question as guidance:
        - First and Last line of the stem may be the same if the stem is only one line.
        - From the first line, identify the exact substring where the wanted text begins, and put it in `start`.
        - From the last line, identify the exact substring where the wanted text ends and put it in `end`.
        - These two substrings will be used to find the start and end index using regex afterwards, so try to use as few words as possible.
        - Overlapping between start and end is allowed.

    Example #1:
        first line: "1. A man is going up hill at 1m/s"
        last line:  "1. A man is going up hill at 1m/s"

        output:
        {{"keep_first_line_from": "A man","keep_last_line_until": "1m/s"}}
    """

llm_task_trim_part = f"""
    You will be given the full text of a question, extracted from a markdown file using line numbers.
    Assuming the extracted text is correct, then only the start of the first and the end of last lines may contain unwanted text.
    The first and last lines may contain unwanted text, such as:
        - Question numbering (e.g. "1.", "2.", "(a)", "(b)", "i.", "ii.", etc.)
        - Text from the previous or next question.
    We want to remove this unwanted text.

    Focus only on one sub-question (part) of the question, specified later.

    Your task is to, using the full question as guidance:
        - First and Last line of the sub-question may be the same if the sub-question is only one line.
        - From the first line, identify the exact substring where the wanted text begins, and put it in `start`.
        - From the last line, identify the exact substring where the wanted text ends and put it in `end`.
        - These two substrings will be used to find the start and end index using regex afterwards, so try to use as few words as possible.
        - Overlapping between start and end is allowed.

    Example #1:
        first line: "answer the following question: (a) what is his speed?"
        last line:  "answer the following question: (a) what is his speed?"

        output:
        {{"keep_first_line_from": "what","keep_last_line_until": "speed?"}}
    """

llm_task_trim_part_solution = f"""
    You will be given the full text of a question, extracted from a markdown file using line numbers.
    Assuming the extracted text is correct, then only the start of the first and the end of last lines may contain unwanted text.
    The first and last lines may contain unwanted text, such as:
        - Question numbering (e.g. "1.", "2.", "(a)", "(b)", "i.", "ii.", etc.)
        - Text from the previous or next question.
    We want to remove this unwanted text.

    Focus only on one part-solution of a sub-question (part) of the question, specified later.

    Your task is to, using the full question as guidance:
        - First and Last line of the part-solution may be the same if the part-solution is only one line.
        - From the first line, identify the exact substring where the wanted text begins, and put it in `start`.
        - From the last line, identify the exact substring where the wanted text ends and put it in `end`.
        - These two substrings will be used to find the start and end index using regex afterwards, so try to use as few words as possible.
        - Overlapping between start and end is allowed.

    Example #1:
        first line: "A: (a) 2 + 3 = 5"
        last line:  "A: (a) 2 + 3 = 5"

        output:
        {{"keep_first_line_from": "A:","keep_last_line_until": "= 5"}}
    """


def trim_question(question: tuple[int, Set_Question_With_Solution]) -> Set_Question_With_Solution:
    question_number, question = question
    question_number += 1

    def trim_question_content(content_text: str) -> str:

        if content_text == "":
            return content_text

        # split_content = content_text.split("\n")
        content_parser = PydanticOutputParser(pydantic_object=TrimPosition)

        trim_content_prompt = f"""
            Your task is to extract a JSON with the following structure exactly, ready to be parsed by a pydantic model:
            {content_parser.get_format_instructions()}

            {llm_task_trim_content}

            Full question:
            {question}

            Stem (content) of the question to extract from:
            {content_text}

            Return the JSON now.
            """
        
        for attempt_idx in range(3):

            response = llm_mini.invoke(trim_content_prompt)

            try:
                parsed_output = content_parser.parse(response.content)
                start = content_text.index(parsed_output.start)
                end   = content_text.index(parsed_output.end) + len(parsed_output.end)
                print(f"Successfully trimmed the stem of question {question_number}.")

                return improve_trim(content_text, start, end)
            except Exception as e:
                print(f"Error parsing LLM response as JSON for trimming content of question {question_number}:")
                print(f"Retrying... Attempt No.{attempt_idx + 1}")
                time.sleep(2)
        else:
            print("Final LLM Response:")
            print(response.content)
            raise Exception("Failed to parse LLM response as JSON after multiple attempts for trimming content.")

    def trim_question_part(part: tuple[int, str]) -> str:
        part_number, part_text = part
        part_number += 1
        if part_text == "":
            return part_text
        
        # split_part = part_text.split("\n")
        part_parser = PydanticOutputParser(pydantic_object=TrimPosition)

        trim_part_prompt = f"""
            Your task is to extract a JSON with the following structure exactly, ready to be parsed by a pydantic model:
            {part_parser.get_format_instructions()}

            {llm_task_trim_part}

            Full question:
            {question}

            specific sub-question (part) of the question to extract from is part {part_number+1}:
            {part_text}

            Return the JSON now.
            """
        
        for attempt_idx in range(3):

            response = llm_mini.invoke(trim_part_prompt)

            try:
                parsed_output = part_parser.parse(response.content)
                start = part_text.index(parsed_output.start)
                end   = part_text.index(parsed_output.end) + len(parsed_output.end)
                print(f"Successfully trimmed part of question {question_number}, part {part_number}.")

                return improve_trim(part_text, start, end)
            except Exception as e:
                print(f"Error parsing LLM response as JSON for trimming part for question {question_number}, part {part_number}")
                print(f"Retrying... Attempt No.{attempt_idx + 1}")
                time.sleep(2)
        else:
            print("Final LLM Response:")
            print(response.content)
            raise Exception("Failed to parse LLM response as JSON after multiple attempts for trimming part.")

    def trim_question_part_solution(solution: tuple[int, str]) -> str:
        part_number, solution_text = solution
        part_number += 1
        if solution_text == "":
            return solution_text
        
        # split_solution = solution_text.split("\n")
        solution_parser = PydanticOutputParser(pydantic_object=TrimPosition)

        trim_solution_prompt = f"""
            Your task is to extract a JSON with the following structure exactly, ready to be parsed by a pydantic model:
            {solution_parser.get_format_instructions()}

            {llm_task_trim_part_solution}

            Full question:
            {question}

            Specific part-solution of the question to extract from is part {part_number+1}:
            {solution_text}

            Return the JSON now.
            """
        
        for attempt_idx in range(3):

            response = llm_mini.invoke(trim_solution_prompt)

            try:
                parsed_output = solution_parser.parse(response.content)
                start = solution_text.index(parsed_output.start.replace('\\\\', '\\'))
                end   = solution_text.index(parsed_output.end.replace('\\\\', '\\')) + len(parsed_output.end)
                print(f"Successfully trimmed part-solution for question {question_number}, part {part_number}.")

                return improve_trim(solution_text, start, end)
            except Exception as e:
                print(f"Error parsing LLM response as JSON for trimming solution part for question {question_number}, part {part_number}")
                print(response.content)
                print(f"Retrying... Attempt No.{attempt_idx + 1}")
                time.sleep(2)

        else:
            print("Final LLM Response:")
            print(response.content)
            raise Exception("Failed to parse LLM response as JSON after multiple attempts for trimming solution part.")

    question.content = trim_question_content(question.content)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        question.parts = list(executor.map(trim_question_part, enumerate(question.parts)))
        question.parts_solutions = list(executor.map(trim_question_part_solution, enumerate(question.parts_solutions)))

    return question

def trim_text(set_questions: Set_Lines) -> Set_Lines:

    with concurrent.futures.ThreadPoolExecutor() as executor:
        set_questions.questions = list(executor.map(trim_question, enumerate(set_questions.questions)))

    return set_questions


# In[21]:


def md_to_json(md_content: str) -> dict:
    """
    Extracts the title and individual questions from a tutorial sheet.
    
    Args:
        md_content (str): The content of a set.
        
    Returns:
        dict: A dictionary containing the keys "name" and "exercise".
              If parsing fails, returns None.
    """

    md_content_lines = convert_markdown_to_classes_by_lines(md_content)

    # corrected_md_content = correct_mistakes_in_markdown(md_content)
    # print("Markdown content corrected for spelling, grammar, and structure.")

    set_lines = llm_extract_questions_lines(md_content_lines)
    print((json.dumps(set_lines.model_dump())))

    set_questions = extract_parts_question(set_lines)
    print(json.dumps(set_questions.model_dump()))

    reduced_dict = dupe_text_reduce(set_questions)
    return trim_text(reduced_dict).model_dump()


# In[22]:


full_json_question_set = md_to_json(md_content)


# # Displaying questions

# In[23]:


# Extract title
title = full_json_question_set["name"] + " " + full_json_question_set["year"]

# Print the title
print(f"Title: {title}\n")

# Extract questions
questions = full_json_question_set["questions"]

# Loop over and print each question
for question_idx, question in enumerate(questions, start=1):
    print(f"**Question {question_idx}**:\n{question.get('title')}\n")
    print(f"Content: {question.get('content')}\n")
    for part_idx, (part_question, part_answer) in enumerate(zip(question.get("parts", []), question.get("parts_solutions", [])), start=1):
        print(f"Question {question_idx}:")
        print(f"- Subquestion {part_idx}: {part_question}")
        print(f"- Worked Solution {part_idx}: {part_answer}")
        print("\n")
    print("-" * 40)  # Separator for readability


# # in2lambda to JSON

# In[24]:


questions = full_json_question_set["questions"]

in2lambda_set = []

# Loop over all questions and question_answers and use in2lambda API to create a JSON.
for question_idx, question_dict in enumerate(questions, start=1):
    parts = []

    for part_question, part_solution in zip(question_dict.get("parts", []), question_dict.get("parts_solutions", [])):
        part_obj = Part(
            text=part_question,
            worked_solution=part_solution
        )
        parts.append(part_obj)

    # Handle image paths - ensure they exist
    image_paths = []
    for img in question_dict.get("images", []):
        if img.startswith("http"):
            # Skip URLs that weren't processed
            continue
        full_path = f"{media_path}/{img}"
        if Path(full_path).exists():
            image_paths.append(full_path)
        else:
            print(f"Warning: Image file not found: {full_path}")

    question = Question(
        title=question_dict.get("title", f"Question {question_idx}"),
        main_text=question_dict.get("content", ""),
        parts=parts,
        images=image_paths
    )
    in2lambda_set.append(question)

try:
    Set(questions=in2lambda_set).to_json(f"{output_path}/out")
    print("JSON output successfully created.")
except Exception as e:
    print(f"Error creating JSON output: {e}")

