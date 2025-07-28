package validator

import parsley.quick.*
import parsley.syntax.zipped.*
import parsley.expr.chain
import parsley.expr.{precedence, Ops, InfixL}
import parsley.errors.ErrorBuilder
import parsley.errors.combinator.*

import lexer.{fully, text}
import lexer.implicits.implicitSymbol
import Block.*

object parser {
  def parse[Err: ErrorBuilder](input: String): Either[Err, MarkDown] = parser.parse(input).toEither

  private lazy val parser = fully(markDown)

  private lazy val markDown = MarkDown(blocks)

  private lazy val blocks = many(block)

  // Define the block parser that recognizes different types of blocks
  private lazy val block: Parsley[Block] = 
    Display(display) |
    Inline(inline) |
    Text(lexer.text)

  // Define the display math parser that recognizes display math blocks
  private lazy val display = "$$".label("Opening display math delimiter") ~> lexer.text <~ "$$".label("Closing display math delimiter")

  // Define the inline math parser that recognizes inline math blocks
  private lazy val inline = "$".label("Opening inline math delimiter") ~> lexer.text <~ "$".label("Closing inline math delimiter")
}