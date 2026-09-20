# Sources to freeze

Each folder here is one document for `in2lambda source add` to freeze, beside the block list
it should write into `source.draft.json`, the draft being named after the source it was frozen
from. `markdown`, `tex` and `docx` say the same thing in the three
formats the command takes, so that what a heading or a list item comes out as does not depend on
which format an author brought it in; `empty_list_item` is a bullet with nothing in it, which has
no position of its own and so no block; `unseparated_list` is a list with no blank line before it,
which pandoc reports as part of the paragraph above, so that paragraph's block has to stop where
the list starts rather than where pandoc says it ends; `display_maths` is a `.tex` with display
maths standing alone, mid-sentence and inside a list item, and a paragraph well over 72 columns
whose inline maths would straddle the wrap, which is what the unwrapped freeze and the `$$`
rewrite below are there for; `crlf` is the `markdown` case saved with
Windows line endings, which is what a document off a teacher's machine usually has, and it has to
freeze to the same blocks and to a hash that `sha256sum source.md` reproduces. The `.gitattributes`
at the top of the repository is what stops a checkout rewriting those endings away.

To cover another construct, add a folder: one `source.md`, `source.tex` or `source.docx`, and
the `expected.json` the test compares the draft's `blocks` against.

The line ranges of the `.tex` and `.docx` cases are ranges in the markdown pandoc writes, not
in the document itself, so they move if pandoc's `commonmark_x` writer changes. They were
produced with **pandoc 3.9.0.2**.

That markdown is written with `--wrap=none`, so a paragraph is one line however long it is and
an inline `$ ... $` is never broken over two, and each `$$ ... $$` the writer put on one line is
moved onto lines of its own afterwards - indented to the item's width where it is in a list, so
the item still holds it. Both are habits of pandoc's writer rather than anything the author did,
and both are maths that Lambda Feedback will not render, so a field quoted out of a freeze that
kept them would fail `in2lambda validate`.

`docx/source.docx` was made from `markdown/source.md` with `pandoc source.md -o source.docx`,
run beside a `figure.png` so that the image is embedded rather than dropped, and with the
image's alt text removed: pandoc turns a captioned image into a figure, which `commonmark_x`
can only write as raw HTML, and the block would then be `other` rather than `image`. A Word
image usually has no alt text, so this is also the ordinary case.

The image the docx embeds is referenced as `media/rId9.png`, which is not extracted - nothing
here reads the image, only the lines around it.
