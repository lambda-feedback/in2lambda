# Sources to freeze

Each folder here is one document for `in2lambda source add` to freeze, beside the block list
it should write into `source.draft.json`, the draft being named after the source it was frozen
from. `markdown`, `tex` and `docx` say the same thing in the three
formats the command takes, so that what a heading or a list item comes out as does not depend on
which format an author brought it in; `empty_list_item` is a bullet with nothing in it, which has
no position of its own and so no block; `unseparated_list` is a list with no blank line before it,
which pandoc reports as part of the paragraph above, so that paragraph's block has to stop where
the list starts rather than where pandoc says it ends; `display_maths` is a `.tex` with display
maths standing alone, mid-sentence, on a list item's first line and as an item's own second
paragraph, each of which the `$$` rewrite below puts on three lines, a display maths opened on
an item's first line and closed on the continuation line below it, which the rewrite puts on
four lines, an inline `$ ... $` the author broke over two lines, which the freeze joins onto
one, and a paragraph well over
72 columns, whose block is the one line the unwrapped freeze leaves it as rather than the two
pandoc's own wrapping made of it; `crlf` is the `markdown` case saved with
Windows line endings, which is what a document off a teacher's machine usually has, and it has to
freeze to the same blocks and to a hash that `sha256sum source.md` reproduces. The `.gitattributes`
at the top of the repository is what stops a checkout rewriting those endings away.

Three of the documents nest blocks inside blocks. `nested_list` is a question written as a list
item holding a paragraph, a list of two parts and a heading, and pins the dotted ids, the `depth`
each carries and that `b2` spans `b2.1` to `b2.4` while `b2.2` spans `b2.2.1` and `b2.2.2`. Its
last item holds one paragraph and stays one block, which is what keeps a document with no nesting
in it freezing to the blocks it always did. `fenced_div` is a `.tex` whose `solution` environment
pandoc writes as `::: {.solution}`, once inside a list item and once holding a list of its own, and
pins that a div's range is the lines its content stands on rather than the `:::` lines around it.
`display_maths`, described above, is the one that pins that an item nesting no list splits as
well: three of its four items hold a paragraph, display maths and a paragraph, and so hold the
three blocks `b7.1` to `b7.3`, `b8.1` to `b8.3` and `b9.1` to `b9.3`. Its fourth item holds one
paragraph and stays the single block `b10`.

To cover another construct, add a folder: one `source.md`, `source.tex` or `source.docx`, and
the `expected.json` the test compares the draft's `blocks` against.

The line ranges of the `.tex` and `.docx` cases are ranges in the markdown pandoc writes, not
in the document itself, so they move if pandoc's `commonmark_x` writer changes. They were
produced with **pandoc 3.9.0.2**.

That markdown is written with `--wrap=none`, so a paragraph is one line however long it is. Each
`$$ ... $$` is then moved onto lines of its own - indented to the item's content column where the
maths stands in a list, so the item still holds it - whether pandoc wrote the maths on one line
or opened it on one line and closed it on the line below, which is what pandoc writes where the
author broke a line inside the maths. The lines of an inline `$ ... $` the author broke are
joined with a space. Lambda Feedback renders none of the three forms, so a field quoted out of a
freeze that kept pandoc's wrapping, the one-line `$$ ... $$` or the newline inside an inline
`$ ... $` would fail `in2lambda validate`.

A `$$` that opens or closes on a pipe table's row, on a block quote's line or on a code block's
line is left as pandoc wrote it: a table cell cannot hold a block, the inserted lines would carry
no `> ` and so fall outside the quote, and a code block's `$$` is characters the document shows
rather than maths it renders. A code block is a line indented four past the content column of the
list item it stands in, which is how an item's own paragraph - indented four itself - is told from
code nested inside the item.

A `$$ ... $$` holding a backtick, or running across a blank line, is left as pandoc wrote it as
well: display maths holds neither, so the two delimiters are an unpaired `$$` - one in inline
code, say - and the opening `$$` of a later maths, and rewriting them would make a maths block of
the words between. The later maths is then left as written too. `in2lambda validate` reports the
maths left as written in any of these places.

`docx/source.docx` was made from `markdown/source.md` with `pandoc source.md -o source.docx`,
run beside a `figure.png` so that the image is embedded rather than dropped, and with the
image's alt text removed: pandoc turns a captioned image into a figure, which `commonmark_x`
can only write as raw HTML, and the block would then be `other` rather than `image`. A Word
image usually has no alt text, so this is also the ordinary case.

The image the docx embeds is referenced as `media/rId9.png`, which is not extracted - nothing
here reads the image, only the lines around it.
