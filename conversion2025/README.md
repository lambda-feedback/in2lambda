This is a folder where we'll generate a 'wizard' to automatically process input documents ready for in2lambda to reacte a JSON (or to directly create a JSON)

We'll work on this branch 'hackathon'


# README

## Overview
This Jupyter Notebook (`sandbox.ipynb`) is designed for processing scientific documents, extracting mathematical expressions, and formatting them in Markdown. It leverages Azure OpenAI's LLM capabilities for text transformation.

## Features
- Loads PDFs and extracts text using `UnstructuredPDFLoader` and `PyMuPDF`.
- Converts mathematical expressions into properly formatted Markdown.
- Uses `langchain` and `AzureChatOpenAI` for text processing.
- Supports structured output parsing using `pydantic`.

## Requirements
Ensure you have the following installed:
- Python 3.8+
- `pip install -r requirements.txt`
- `langchain`, `langchain_openai`, `pydantic`, `dotenv`, `PyMuPDF`, `PIL`

## Setup
1. Create a `.env` file in the root directory and add your Azure OpenAI API keys:
   ```env
   AZURE_OPENAI_API_KEY=<your-api-key>
   AZURE_OPENAI_ENDPOINT=<your-endpoint>
   ```
4. Open `sandbox.ipynb` and execute the cells to process your documents.

## Notes
- Ensure your API key and endpoint are correct, as they are required for LLM functionality.
- The notebook is designed for scientific documents, but can be extended to other text formats.



