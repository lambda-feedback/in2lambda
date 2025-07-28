import munit.FunSuite

import Block.* 

class MainSpec extends FunSuite {
  // syntax checking
  // valid tests
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

  test("display math with newlines") {
    val result = parser.parse("$$\nE = \nmc^2\n$$")
    assertEquals(result, Right(MarkDown(List(Display("E = \nmc^2\n")))))
  }

  // test ("allow escaped dollar signs in inline math") {
  //   val result = parser.parse("$ x + \\$y = z $")
  //   assertEquals(result, Right(MarkDown(List(Inline("x + $y = z ")))))
  // }

  // test ("allow escaped dollar signs in display math") {
  //   val result = parser.parse("$$ x + \\$y = z $$")
  //   assertEquals(result, Right(MarkDown(List(Display("x + $y = z ")))))
  // }


  // invalid tests
  test("missing closing inline math delimiter") {
    val result = parser.parse("$ x + y = z")
    assert(result.isLeft)
  }

  test("missing closing display math delimiter") {
    val result = parser.parse("$$ x + y = z")
    assert(result.isLeft)
  }

  test("missing opening inline math delimiter") {
    val result = parser.parse("x + y = z $")
    assert(result.isLeft)
  }

  test("missing opening display math delimiter") {
    val result = parser.parse("x + y = z $$")
    assert(result.isLeft)
  }

  test("inline math inside display math") {
    val result = parser.parse("$$ x + $y$ = z $$")
    assert(result.isLeft)
  }

  test("display math inside inline math") {
    val result = parser.parse("$ x + $$y$$ = z $")
    assert(result.isLeft)
  }


  // semantic checking
  test("valid inline math without newlines") {
    val markdown = MarkDown(List(Inline("x + y = z")))
    assert(validate_markdown(markdown))
  }
  
  test("invalid inline math with newlines") {
    val markdown = MarkDown(List(Inline("x + \ny = z")))
    assert(!validate_markdown(markdown))
  }

  test("valid markdown with mixed content") {
    val markdown = MarkDown(List(Text("Hello"), Inline("x + y"), Display("E = mc^2")))
    assert(validate_markdown(markdown))
  }

  test("allows display math with newlines") {
    val markdown = MarkDown(List(Display("E = mc^2\n")))
    assert(validate_markdown(markdown))
  }

  // rebuilding markdown
  test("rebuild markdown from parsed structure") {
    val markdown = MarkDown(List(Text("Hello"), Inline("x + y"), Display("E = mc^2")))
    val rebuilt = rebuild_markdown(markdown)
    assertEquals(rebuilt, "Hello$x + y$\n$$\nE = mc^2\n$$\n")
  }

}