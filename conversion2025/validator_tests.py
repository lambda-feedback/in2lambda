from validator import math_delimiter_checker

import unittest


class TestMathDelimiterChecker(unittest.TestCase):

    # single dollar sign tests
    # valid tests
    def test_valid_single_dollar_with_period(self):
        content = "This is an inline math expression: $x = y$."
        self.assertTrue(math_delimiter_checker(content))
        
    def test_valid_single_dollar_end_of_string(self):
        content = "This is an inline math expression: $x = y$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar_at_beginning(self):
        content = "$x = y$, this is an inline math expression."
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar_with_newline_after(self):
        content = "$x = y$\n"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar_with_newline_before(self):
        content = "\n$x = y$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_multiple_single_dollar_expressions(self):
        content = "First expression $x = y$ and second expression $a = b$."
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar_with_special_chars(self):
        content = "Expression: $\\alpha + \\beta = \\gamma$."
        self.assertTrue(math_delimiter_checker(content))

    # invalid tests
    def test_no_closing_single_dollar(self):
        content = "This is an inline math expression: $x = y."
        self.assertFalse(math_delimiter_checker(content))

    def test_no_opening_single_dollar(self):
        content = "This is an inline math expression: x = y$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_newline_in_inline_middle(self):
        content = "This is an inline math expression:$x \n= y$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_newline_in_inline_beginning(self):
        content = "This is an inline math expression:$\nx = y$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_newline_in_inline_end(self):
        content = "This is an inline math expression:$x = y\n$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_incorrect_closing_single_dollar_delimiter(self):
        content = "Expression $x = y$$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_odd_number_single_dollars(self):
        content = "Expression $x = y$ and $a = b$ and $c ="
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_triple_dollar(self):
        content = "Expression $$$x = y$$$."
        self.assertFalse(math_delimiter_checker(content))

    # double dollar sign tests
    # valid tests
    def test_valid_double_dollar_end_of_string(self):
        content = "This is a display math expression:\n$$\nx = y\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_double_dollar_at_beginning(self):
        content = "$$\nx = y\n$$\n, this is a display math expression."
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_double_dollar_multiple_lines(self):
        content = "Display math:\n$$\nx = y\n\na = b\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_double_dollar_empty_content(self):
        content = "Expression:\n$$\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_mixed_delimiters(self):
        content = "Inline $x = y$ and display math:\n$$\nx = y\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_multiple_double_dollar_blocks(self):
        content = "First:\n$$\nx = y\n$$\nSecond:\n$$\na = b\n$$"
        self.assertTrue(math_delimiter_checker(content))
    
    # invalid tests
    def test_no_closing_double_dollar(self):
        content = "This is a display math expression:\n$$\nx = y\n"
        self.assertFalse(math_delimiter_checker(content))

    def test_no_opening_double_dollar(self):
        content = "This is a display math expression:\nx = y\n$$"
        self.assertFalse(math_delimiter_checker(content))

    def test_no_newline_before_double_dollar(self):
        content = "This is a display math expression:$$\nx = y\n$$."
        self.assertFalse(math_delimiter_checker(content))

    def test_valid_no_newline_after_double_dollar(self):
        content = "This is a display math expression:\n$$\nx = y\n$$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_text_after_opening_double_dollar(self):
        content = "Expression:\n$$text\nx = y\n$$"
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_text_before_closing_double_dollar(self):
        content = "Expression:\n$$\nx = y\ntext$$"
        self.assertFalse(math_delimiter_checker(content))
        
    def test_invalid_incorrect_closing_double_dollar_delimiter(self):
        content = "Expression $$x = y$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_mixed_single_double_mismatch(self):
        content = "Expression $x = y$$"
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_mixed_double_single_mismatch(self):
        content = "Expression $$x = y$"
        self.assertFalse(math_delimiter_checker(content))

    # edge cases
    def test_empty_string(self):
        content = ""
        self.assertTrue(math_delimiter_checker(content))

    def test_only_text_no_math(self):
        content = "This is just regular text with no math expressions."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_signs(self):
        content = "This costs \\$5 and that costs \\$10."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_single_with_math(self):
        content = "Price is \\$10 and math is $x = y$."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_multiple_with_math(self):
        content = "Prices are \\$5, \\$10 and math is $x = y$."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_double_with_display_math(self):
        content = "Price \\$100:\n$$\nx = y\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_double_dollar(self):
        content = "This symbol \\$\\$ is not math."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_at_beginning(self):
        content = "\\$100 is expensive."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_at_end(self):
        content = "It costs \\$"
        self.assertTrue(math_delimiter_checker(content))

    def test_mixed_escaped_and_unescaped_dollars(self):
        content = "Price \\$50 for $x + y = z$ calculation."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_in_math_expression(self):
        content = "Expression: $cost = \\$100$."
        self.assertTrue(math_delimiter_checker(content))

    def test_escaped_dollar_in_display_math(self):
        content = "Display:\n$$\ncost = \\$100\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_multiple_consecutive_escaped_dollars(self):
        content = "Multiple prices: \\$5, \\$10, \\$15."
        self.assertTrue(math_delimiter_checker(content))


if __name__ == '__main__':
    unittest.main()