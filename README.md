# in2lambda

[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/lambda-feedback/in2lambda/test.yml?style=flat-square&logo=github&label=tests)](https://github.com/lambda-feedback/in2lambda/actions/workflows/test.yml)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/lambda-feedback/in2lambda/deploy-docs.yml?style=flat-square&logo=googledocs&logoColor=white&label=docs)](https://lambda-feedback.github.io/in2lambda/)

in2lambda is a Python command line tool and library that automagically uploads questions to [Lambda Feedback](https://lambdafeedback.com/).

Find out more in the [documentation](https://lambda-feedback.github.io/in2lambda/).

```
$ pip install in2lambda
```

## Building sets with an AI agent

An agent can build problem sets from source documents with in2lambda. [AGENTS.md](AGENTS.md) holds the rules it follows. An example prompt:

```
Build Lambda Feedback problem sets with in2lambda (https://github.com/lambda-feedback/in2lambda), main branch. Follow its AGENTS.md.

Inputs: [N] PDFs, one per set, and one PDF of all questions with solutions.

1. Build Set 1 only, send the zip and stop. I will upload it and report back.
2. After I confirm, build the remaining sets without stopping.
3. Do not resend a set unless I ask.

Reply with the zips, the changes you made to the source, and anything unconfirmed on the platform.
```
