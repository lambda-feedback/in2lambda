class ValidatorError(Exception):
    pass

class Passed(ValidatorError):
    pass

class MissingNewLineBeforeOpeningDisplayMathDelimiter(ValidatorError):
    pass

class MissingNewLineAfterOpeningDisplayMathDelimiter(ValidatorError):
    pass

class DoubleDollarInsteadOfClosingSingleDollar(ValidatorError):
    pass

class MissingClosingDoubleDollarInsteadOfSingleDollar(ValidatorError):
    pass

class MissingNewLineBeforeClosingDisplayMathDelimiter(ValidatorError):
    pass

class MissingNewLineAfterClosingDisplayMathDelimiter(ValidatorError):
    pass

class InvalidNewlineInsideInlineMathExpression(ValidatorError):
    pass

class MissingClosingSingleDollar(ValidatorError):
    pass

class MissingClosingDoubleDollar(ValidatorError):
    pass
