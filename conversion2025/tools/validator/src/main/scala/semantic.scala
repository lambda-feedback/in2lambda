import Block.*

// check that the inline math does not contain newlines
def inline_check(math: String): Boolean = !math.contains('\n')

// validate the markdown content
def validate_markdown(markdown: MarkDown): Boolean = {
    markdown.content.forall {
        case Inline(m) => inline_check(m)
        case _         => true
    }
}

private val INLINE_DELIM = "$"
private val DISPLAY_DELIM = "\n$$\n"

// Rebuild the markdown content from the parsed structure
def rebuild_markdown(markdown: MarkDown): String = {
    markdown.content.map {
        case Text(s) => s
        case Inline(m) => s"${INLINE_DELIM}${m}${INLINE_DELIM}"
        case Display(m) => s"${DISPLAY_DELIM}${m.trim}${DISPLAY_DELIM}"
    }.mkString
}