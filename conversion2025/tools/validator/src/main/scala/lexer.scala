import parsley.Parsley
import parsley.token.{Lexer, Basic}
import parsley.token.descriptions.*
import parsley.errors.combinator.*

// Define the lexer with a custom lexical description
object lexer {

    // Define the set of generic keywords
    private val genericKeywords = Set(
        "$$", "$"
    )

    // Define the lexical description
    private val desc = LexicalDesc.plain.copy(
        // Define how identifiers and symbols are recognized
        nameDesc = NameDesc.plain.copy(
            identifierStart = Basic(x => x.isInstanceOf[Char] && x != '$'),
            identifierLetter = Basic(x => x.isInstanceOf[Char] && x != '$'),
        ),

        // Define how symbols are recognized
        symbolDesc = SymbolDesc.plain.copy(
            hardOperators = genericKeywords
        )
    )

    private val lexer = Lexer(desc)

    def fully[A](p: Parsley[A]): Parsley[A] = lexer.fully(p)

    // Define the text parser that recognizes regular text
    val text: Parsley[String] = lexer.lexeme.names.identifier
    
    // Define the symbol parser that recognizes symbols
    val implicits = lexer.lexeme.symbol.implicits
}