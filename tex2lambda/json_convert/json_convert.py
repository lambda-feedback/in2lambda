import json
import os
import zipfile
from copy import deepcopy
from pathlib import Path
import shutil

MINIMAL_TEMPLATE = "minimal_template.json"


def converter(template, ListQuestions, output_dir):
    # Create output by copying template
    
   

    for i in range(len(ListQuestions)):
        output = deepcopy(template)

        # add title to the question file
        if ListQuestions[i]["Title"] != "":
            output["title"] = ListQuestions[i]["Title"]
        else:
            output["title"] = "Question " + str(i+1)

        # add main text to the question file
        output["masterContent"]["blocks"][0]["data"] = ListQuestions[i]["MainText"]

        # add parts to the question file
        output["parts"][0]["content"]["blocks"][0]["data"] = ListQuestions[i]["Parts"][
            0
        ]["Text"]
        output["parts"][0]["workedSolution"][0]["content"]["blocks"][0][
            "data"
        ] = ListQuestions[i]["Parts"][0]["Answer"]
        for j in range(1, len(ListQuestions[i]["Parts"])):
            output["parts"].append(deepcopy(template["parts"][0]))
            output["parts"][j]["content"]["blocks"][0]["data"] = ListQuestions[i][
                "Parts"
            ][j]["Text"]
            output["parts"][j]["workedSolution"][0]["content"]["blocks"][0][
                "data"
            ] = ListQuestions[i]["Parts"][j]["Answer"]

        # Output file)
        filename = "Question " + str(i+1)

        #create directory to put the questions
        os.makedirs(output_dir, exist_ok=True)
        output_question=os.path.join(output_dir,filename)
        os.makedirs(output_question,exist_ok=True)

        #create directory to put image
        output_image=os.path.join(output_question,'media')
        os.makedirs(output_image,exist_ok=True)
      

        #write questions into directory
        with open(f"{output_question}/{filename}.json", "w") as file:
            json.dump(output, file)

        #write image into directory 
        for k in range(len(ListQuestions[i]['Images'])):
            image_path=os.path.abspath(ListQuestions[i]['Images'][k]) #converts computer path into python path
            shutil.copy(image_path,output_image) #copies image into the directory
    
        #output zip file in destination folder
        shutil.make_archive(output_question, 'zip', output_question) 
        
      


def main(questions, output_dir):
    # Use path so minimal template can be found regardless of where the user is running python from.
    with open(Path(__file__).with_name(MINIMAL_TEMPLATE), "r") as file:
        template = json.load(file)
    converter(template, questions, output_dir)
