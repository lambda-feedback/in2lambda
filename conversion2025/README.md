# README

## Overview
This Jupyter Notebook (`converter.ipynb`) is designed for processing question sets and tutorials, extracting mathematical expressions, formatting them in Markdown then converting it into Lambda Feedback compatible JSONs. It leverages Mathpix, OpenAI's LLM capabilities and post processing for text transformation.

## Requirements
Ensure you have the following installed:
- Python 3.8+
- `pip install -r requirements.txt`

## Setup
1. Create a `.env` file in the root directory and add your OpenAI and MathPix API keys:
   ```env
   OPENAI_API_KEY=<your-openai-api-key>
   MATHPIX_API_KEY=<your-mathpix-key>
   MATHPIX_APP_ID=<your-mathpix-id>
   ```
2. Open `converter.ipynb` and execute the cells to process your documents.

#### Notes
- Ensure your API keys are correct, as they are required for LLM functionality.

## How to use
1. Place a pdf (the set of questions) of your choice into the folder, `/conversion_content/input`.

2. Ensure only 1 pdf is within the ./input folder, as the converter chooses one pdf in the folder in an undefined manner (likely alphabetically).

3. Run the converter in Jupiter. The folder `/conversion_content/converter` will be created if it does not exist yet.

#### Convertion process
1. Within `/conversion_content/converter`, it will create another folder, `converter/conversion_content/media`, this will hold all the images that MathPix extracted.

2. A file called `exmaple.md` will be made within  `/conversion_content/converter` if it does not exist yet, this is the markdown file produced by MathPix after scanning the pdf.

3. Note that the current program will keep using the same `example.md` unless it is deleted, this is to reduce MathPix tokens as it almost alway produce identical markdown files with the same pdf.
This means that to convert a different pdf file, you must also delete `example.md`.

#### Notes
Please read `assumptions.txt` for things that the converter assumes. If these assumptions are not obeyed, the converter may struggle and produce odd results.

## Evaluation
I believe this converter should be able to be integrated with the platform's API.

The converter does have its flaws and there are definitely areas it can still improve on, such as being able to reliably taking in extremely messy inputs or produce more than just questions and solutions (answer box).

Within the boundary of its assumptions however, it works very reliably and well.
