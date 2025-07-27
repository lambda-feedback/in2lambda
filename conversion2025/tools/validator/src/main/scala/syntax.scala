import parsley.generic

// This file defines the lexer for parsing mathematical expressions in Markdown format.
case class MarkDown(content: List[Block])
object MarkDown extends generic.ParserBridge1[List[Block],MarkDown]

enum Block {
    case Text(content: String)    // Regular text block
    case Inline(content: String)  // Inline Math block
    case Display(content: String) // Display Math block
}

object Block {
    object Text extends generic.ParserBridge1[String,Block]
    object Inline extends generic.ParserBridge1[String,Block]
    object Display extends generic.ParserBridge1[String,Block]
}