import parsley.Parsley
import parsley.token.{Lexer, Basic}
import parsley.token.descriptions.*
import parsley.errors.combinator.*


object lexer {
    private val genericKeywords = Set(
        "$$", "$"
    )

    private val desc = LexicalDesc.plain.copy(
        nameDesc = NameDesc.plain.copy(
            identifierStart = Basic(_.isInstanceOf[Char]),
            identifierLetter = Basic(_.isInstanceOf[Char]),
        ),
        symbolDesc = SymbolDesc.plain.copy(
            hardOperators = genericKeywords,
        )
    )

    private val lexer = Lexer(desc)

    def fully[A](p: Parsley[A]): Parsley[A] = lexer.fully(p)

    val text: Parsley[String] = lexer.lexeme.names.identifier
    
    val implicits = lexer.lexeme.symbol.implicits
}