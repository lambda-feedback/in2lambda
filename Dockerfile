FROM python:3.12.1-alpine AS python-builder

ENV PYTHONUNBUFFERED=1 \
    # Prevents Python from buffering stdout and stderr
    PYTHONDONTWRITEBYTECODE=1 \
    # prevents python creating .pyc files
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# README required since referenced by pyproject.toml
COPY ./pyproject.toml ./README.md ./in2lambda /app/
COPY ./in2lambda /app/in2lambda/

RUN pip install .

FROM python:3.12.1-alpine

COPY --from=python-builder /usr/local/bin/in2lambda /usr/local/bin/in2lambda
COPY --from=python-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

RUN apk add --no-cache pandoc
