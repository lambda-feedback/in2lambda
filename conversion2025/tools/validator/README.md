# Math Delimiter Validator

A Scala-based validator for mathematical expressions in Markdown format. This tool validates the correct usage of single dollar signs (`$`) for inline math and double dollar signs (`$$`) for display math expressions.

## Features

- **Syntax Validation**: Parses Markdown content to ensure proper math delimiter pairing
- **Semantic Validation**: Enforces rules like no newlines in inline math expressions
- **HTTP Server**: REST API endpoint for validation services
- **Markdown Reconstruction**: Ability to rebuild valid Markdown from parsed structure

## Requirements

- Scala 3.3.1
- sbt 1.11.3
- Java 8 or higher

## Installation

Clone the repository and navigate to the validator directory:

```bash
cd /home/jimbo/lambda/in2lambda/conversion2025/tools/validator
```

## Usage

### Building the Project

```bash
sbt compile
```

### Running Tests

```bash
sbt test
```

### Starting the HTTP Server

```bash
sbt run
```

The server will start on `localhost:8080` with a POST endpoint at `/process`.

### Programmatic Usage

```scala
import parser.*
import Block.*

// Parse markdown content
val result = parser.parse("Hello $x + y = z$ world!")
result match {
  case Right(markdown) => 
    // Validate the parsed content
    if (validate_markdown(markdown)) {
      println("Valid markdown!")
      // Rebuild if needed
      val rebuilt = rebuild_markdown(markdown)
    } else {
      println("Invalid markdown content")
    }
  case Left(error) => 
    println(s"Parse error: $error")
}
```

## Validation Rules

### Inline Math (`$...$`)
- Must be enclosed by single dollar signs
- Cannot contain newline characters
- Example: `$x + y = z$`

### Display Math (`$$...$$`)
- Must be enclosed by double dollar signs
- Can contain newline characters
- Should be on separate lines for proper formatting
- Example:
  ```
  $$
  E = mc^2
  $$
  ```

### Text
- Regular markdown text outside of math expressions
- Dollar signs can be escaped with backslash (`\$`)

## Project Structure

```
src/
├── main/scala/
│   ├── Main.scala          # HTTP server entry point
│   ├── parser.scala        # Main parsing logic using Parsley
│   ├── lexer.scala         # Lexical analysis definitions
│   ├── syntax.scala        # AST definitions for markdown blocks
│   └── semantic.scala      # Validation rules and markdown reconstruction
└── test/scala/
    └── MainTest.scala      # Comprehensive test suite
```

## Dependencies

- **Parsley**: Parser combinator library for syntax analysis
- **http4s**: HTTP server framework
- **cats-effect**: Functional effects library
- **munit**: Testing framework

## API

### POST /process

Processes markdown content and returns validation results.

**Request:**
```
Content-Type: text/plain
Body: Raw markdown content
```

**Response:**
```
Content-Type: text/plain
Body: Processed result
```

## Development

### Adding New Validation Rules

1. Define new error cases in `syntax.scala`
2. Implement validation logic in `semantic.scala`
3. Add corresponding tests in `MainTest.scala`

### Extending the Parser

Modify `parser.scala` and `lexer.scala` to support additional markdown constructs while maintaining compatibility with existing math delimiter rules.

## Testing

The test suite covers:
- Valid and invalid syntax parsing
- Semantic validation rules
- Markdown reconstruction
- Edge cases and error conditions

Run specific test suites:
```bash
sbt "testOnly MainSpec"
```

## License

This project is part of the in2lambda conversion tools.
