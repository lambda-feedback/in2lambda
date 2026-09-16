# 🪄 Wizard

The filters expect a document that already has a clear structure. When you only
have a messy PDF, a Word document or a LaTeX problem sheet, `in2lambda wizard`
uses OCR and an LLM to turn it into the plain `#`/`##` markdown that the
[`Markdown` filter](filters/_autosummary/Markdown) understands.

The wizard **does not** produce Lambda Feedback JSON directly. It writes a
markdown file for you to read and fix, and then you run the normal conversion on
it.

## Setup

The wizard needs the optional `llm` extra:

```bash
$ pip install 'in2lambda[llm]'
```

and these environment variables (a `.env` file in the working directory is
picked up automatically):

| Variable | Needed for | Notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | every run | Create one at <https://openrouter.ai/keys>. |
| `IN2LAMBDA_MODEL` | optional | Default model slug; override per run with `--model`. |
| `MATHPIX_APP_ID`, `MATHPIX_API_KEY` | PDF input only | From <https://mathpix.com/ocr>. |

## Usage

```bash
$ in2lambda wizard problem_sheet.pdf -o draft.md
```

`draft.md` now contains one `#` heading per question, `## Part N` headings for
sub-questions, and `## Solution` blocks. Any figures found in a PDF are saved
next to it under `media/`.

Read through `draft.md`, fix anything the model got wrong, then convert it:

```bash
$ in2lambda convert draft.md Markdown
```

Every set is called `set` unless you say otherwise. Pass `--name` (`-n`) to give
it a distinct name, which is what Lambda Feedback shows on import and also names
the `set_<name>.json` / `<name>.zip` output:

```bash
$ in2lambda convert draft.md Markdown --name "Problem Sheet 4"
```

:::{note}
`.docx`, `.tex` and `.md` inputs skip the OCR step and go straight to the LLM.
:::
