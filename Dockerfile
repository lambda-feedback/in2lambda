FROM python:3.11.4-alpine AS python-builder

ENV PYTHONUNBUFFERED=1 \
    # Prevents Python from buffering stdout and stderr
    PYTHONDONTWRITEBYTECODE=1 \
    # prevents python creating .pyc files
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# README required since referenced by pyproject.toml
COPY ./pyproject.toml ./README.md ./tex2lambda /app/
COPY ./tex2lambda /app/tex2lambda/

RUN pip install .

FROM python:3.11.4-alpine

COPY --from=python-builder /usr/local/bin/tex2lambda /usr/local/bin/tex2lambda
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

RUN apk add --no-cache pandoc
