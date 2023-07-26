import openai
import os
import requests
from bs4 import BeautifulSoup

openai.api_key = os.getenv("katex_convert_API")

def read_txt_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"Error occurred while reading the file: {e}")
        return None

prompt = read_txt_file('tex2lambda\katex_convert\katex_convert(experimental)\prompt.txt')
latex_string = read_txt_file('tex2lambda\katex_convert\katex_convert(experimental)\latex_string.txt')

def generatePrompt(prompt,latex_string):
    return f"""{prompt} + {latex_string}"""

# Scrape KaTeX compatibility information from website
url = 'https://katex.org/docs/support_table.html'
page = requests.get(url)
soup = BeautifulSoup(page.content, 'html.parser')
table = soup.find('table')
rows = table.find_all('tr')
data = []
for row in rows:
    cols = row.find_all('td')
    cols = [ele.text.strip() for ele in cols]
    data.append([ele for ele in cols if ele])

# Convert data to string and format for use as additional context
compatibility_info = '\n'.join([' '.join(row) for row in data])
context = f"KaTeX compatibility information:\n{compatibility_info}"

L=1

for _ in range(L):
    latex_string = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "system", "content": "Assistant is a large language model trained by OpenAI."},
            {"role": "system", "content": context},
            {"role": "user", "content": generatePrompt(prompt,latex_string)}], temperature = 0.1)

print(latex_string)
