# Sources to freeze

Each folder here is one document for `in2lambda source add` to freeze, beside the block list
it should write into `draft.json`. The three say the same thing in the three formats the
command takes, so that what a heading or a list item comes out as does not depend on which
format an author brought it in.

To cover another construct, add a folder: one `source.md`, `source.tex` or `source.docx`, and
the `expected.json` the test compares the draft's `blocks` against.

The line ranges of the `.tex` and `.docx` cases are ranges in the markdown pandoc writes, not
in the document itself, so they move if pandoc's `commonmark_x` writer changes. They were
produced with **pandoc 3.9.0.2**.

`docx/source.docx` was made from `markdown/source.md` with `pandoc source.md -o source.docx`,
run beside a `figure.png` so that the image is embedded rather than dropped, and with the
image's alt text removed: pandoc turns a captioned image into a figure, which `commonmark_x`
can only write as raw HTML, and the block would then be `other` rather than `image`. A Word
image usually has no alt text, so this is also the ordinary case.

The image the docx embeds is referenced as `media/rId9.png`, which is not extracted - nothing
here reads the image, only the lines around it.
