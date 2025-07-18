from validator import math_delimiter_checker

import unittest


class TestMathDelimiterChecker(unittest.TestCase):

    # single dollar sign tests
    # valid tests
    def test_valid_single_dollar(self):
        content = "This is an inline math expression: $x = y$."
        self.assertTrue(math_delimiter_checker(content))
        #
    def test_valid_single_dollar(self):
        content = "This is an inline math expression: $x = y$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar(self):
        content = "$x = y$, this is an inline math expression."
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar(self):
        content = "$x = y$\n"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_single_dollar(self):
        content = "\n$x = y$"
        self.assertTrue(math_delimiter_checker(content))

    # invalid tests
    def test_no_closing_single_dollar(self):
        content = "This is an inline math expression: $x = y."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_newline_in_inline(self):
        content = "This is an inline math expression:$x \n= y$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_newline_in_inline2(self):
        content = "This is an inline math expression:$\nx = y$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_newline_in_inline3(self):
        content = "This is an inline math expression:$x = y\n$."
        self.assertFalse(math_delimiter_checker(content))

    def test_invalid_incorrect_closing_single_dollar_delimiter(self):
        content = "Expression $x = y$$."
        self.assertFalse(math_delimiter_checker(content))


    # double dollar sign tests
    # valid tests
    def test_valid_double_dollar(self):
        content = "This is a display math expression:\n$$\nx = y\n$$."
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_double_dollar2(self):
        content = "This is a display math expression:\n$$\nx = y\n$$"
        self.assertTrue(math_delimiter_checker(content))

    def test_valid_double_dollar(self):
        content = "$$\nx = y\n$$\n, this is a display math expression."
        self.assertTrue(math_delimiter_checker(content))

    def test_mixed_delimiters(self):
        content = "Inline $x = y$ and display math:\n$$\nx = y\n$$"
        self.assertTrue(math_delimiter_checker(content))
    
    # invalid tests
    def test_no_closing_double_dollar(self):
        content = "This is a display math expression:\n$$\nx = y\n"
        self.assertFalse(math_delimiter_checker(content))

    def test_no_newline_before_double_dollar(self):
        content = "This is a display math expression:$$\nx = y\n$$."
        self.assertFalse(math_delimiter_checker(content))

    def test_no_newline_after_double_dollar(self):
        content = "This is a display math expression:\n$$\nx = y\n$$."
        self.assertTrue(math_delimiter_checker(content))
        
    def test_invalid_incorrect_closing_double_dollar_delimiter(self):
        content = "Expression $$x = y$."
        self.assertFalse(math_delimiter_checker(content))


if __name__ == '__main__':
    unittest.main()