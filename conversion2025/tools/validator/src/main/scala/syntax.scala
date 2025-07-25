import parsley.generic

case class MarkDown(content: List[Block])
object MarkDown extends generic.ParserBridge1[List[Block],MarkDown]

enum Block {
    case Text(s: String)    // Regular text block
    case Inline(m: String)  // Inline Math block
    case Display(m: String) // Display Math block
}

object Block {
    object Text extends generic.ParserBridge1[String,Block]
    object Inline extends generic.ParserBridge1[String,Block]
    object Display extends generic.ParserBridge1[String,Block]
}