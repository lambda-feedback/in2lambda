FROM python:3.10

WORKDIR /app

# Install Pandoc
RUN apt-get update && apt-get install -y pandoc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app
COPY app/data/ /app/data
COPY app/outputs/ /app/outputs

COPY . .

EXPOSE 5000

CMD [ "python", "main.py" ]
