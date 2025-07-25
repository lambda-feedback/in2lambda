import munit.FunSuite

import Block.* 

class MainSpec extends FunSuite {
  test("only regular text") {
    val result = parser.parse("Hello world!")
    assertEquals(result, Right(MarkDown(List(Text("Hello world!")))))
  }

  test("only inline math") {
    val result = parser.parse("$ x + y = z $")
    assertEquals(result, Right(MarkDown(List(Inline("$x + y = z$")))))
  }

  test("only display math") {
    val result = parser.parse("$$ x + y = z $$")
    assertEquals(result, Right(MarkDown(List(Display("x + y = z")))))
  }
}