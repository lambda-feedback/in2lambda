import json
import os
import zipfile
from copy import deepcopy
from pathlib import Path

MINIMAL_TEMPLATE = "minimal_template.json"


def converter(template, ListQuestions, output_dir):
    # Create output by copying template
    output = deepcopy(template)

    os.makedirs(output_dir, exist_ok=True)

    # counter for number of loops
    count = 1

    for i in range(0, len(ListQuestions)):
        # add title to the question file
        if ListQuestions[i]["Title"] != "":
            output["title"] = ListQuestions[i]["Title"]
        else:
            output["title"] = "Question " + str(count)

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

        # Output file
        filename = "Question " + str(count)
        with open(f"{output_dir}/{filename}.json", "w") as file:
            json.dump(output, file)
        with zipfile.ZipFile(f"{output_dir}/{filename}.zip", "w") as zipf:
            zipf.write(f"{output_dir}/{filename}.json", arcname=filename + ".json")
        # increase counter
        count = count + 1


def main(questions, output_dir):
    # Use path so minimal template can be found regardless of where the user is running python from.
    with open(Path(__file__).with_name(MINIMAL_TEMPLATE), "r") as file:
        template = json.load(file)
    converter(template, questions, output_dir)
