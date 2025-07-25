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

  private lazy val block: Parsley[Block] = 
    Display(display) |
    Inline(inline) |
    Text(lexer.text)

  private lazy val display = "$$" ~> lexer.text <~ "$$"
  private lazy val inline = "$" ~> lexer.text <~ "$"
}