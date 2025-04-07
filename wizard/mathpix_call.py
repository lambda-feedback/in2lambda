import requests
import json
import os
import time
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()
MATHPIX_API_KEY = os.getenv("MATHPIX_API_KEY")
MATHPIX_APP_ID = os.getenv("MATHPIX_APP_ID")

with open("wizard/pastpapers/2024_paper.pdf", "rb") as file:
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

    url = f"https://api.mathpix.com/v3/pdf/{pdf_id}.mmd"
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
            with open(f"{pdf_id}.mmd", "w") as f:
                f.write(response.text)
            print("Downloaded MMD successfully.")
            break
        else:
            print(f"Attempt {attempt + 1}/{max_retries}: Processing not complete. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    else:
        print("Failed to retrieve processed PDF after multiple attempts:", response.status_code, response.text)