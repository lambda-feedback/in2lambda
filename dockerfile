FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Install Pandoc
RUN apt-get update && apt-get install -y pandoc

# Install Poetry and dependencies needed for building native packages (gcc, etc.)
RUN pip install poetry && \
    apt-get update && \
    apt-get install -y build-essential

# Copy only the poetry.lock and pyproject.toml files initially
COPY pyproject.toml poetry.lock ./

# Install the project's dependencies using Poetry
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# Install the custom package directly from the GitHub repository
RUN pip install https://github.com/lambda-feedback/content-conversion/archive/main.zip

# Copy the application code, data, and outputs directories
COPY app /app

EXPOSE 5000

# CMD [ "python", "main.py" ]
CMD ["python", "main.py", "/app/example.tex", "Materials"]
