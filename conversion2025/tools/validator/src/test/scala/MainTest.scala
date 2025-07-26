import munit.FunSuite

import Block.* 

class MainSpec extends FunSuite {
  test("only regular text") {
    val result = parser.parse("Hello world!")
    assertEquals(result, Right(MarkDown(List(Text("Hello world!")))))
  }

  test("only inline math") {
    val result = parser.parse("$ x + y = z $")
    assertEquals(result, Right(MarkDown(List(Inline("x + y = z ")))))
  }

  test("only display math") {
    val result = parser.parse("$$ x + y = z $$")
    assertEquals(result, Right(MarkDown(List(Display("x + y = z ")))))
  }
  
  test("text, inline and display math together") {
    val result = parser.parse("question 1: $$ x + y = z $$ question 2: $ a + b = c $")
    assertEquals(result, Right(MarkDown(List(Text("question 1: "), Display("x + y = z "), Text("question 2: "), Inline("a + b = c ")))))
  }

  test("inline math with no spaces") {
    val result = parser.parse("$x+y=z$")
    assertEquals(result, Right(MarkDown(List(Inline("x+y=z")))))
  }

  test("display math with no spaces") {
    val result = parser.parse("$$x+y=z$$")
    assertEquals(result, Right(MarkDown(List(Display("x+y=z")))))
  }
}