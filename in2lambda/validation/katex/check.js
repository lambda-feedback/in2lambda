// Renders maths with KaTeX itself, so that what Lambda Feedback's browser would refuse
// is refused here. Reads a JSON array of {"tex": ..., "display": bool} from stdin and
// writes a JSON array of {"index": i, "message": ...} for the ones KaTeX threw on.
//
// One process renders every expression in a set: starting node costs more than the
// rendering does.

const katex = require("./katex.min.js");

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  const rejections = [];

  JSON.parse(input).forEach((expression, index) => {
    try {
      katex.renderToString(expression.tex, {
        displayMode: expression.display,
        strict: true,
        throwOnError: true,
      });
    } catch (error) {
      rejections.push({
        index,
        message: error.message
          // Every message begins "KaTeX parse error: "; the report already says who is
          // speaking, so the constant part is dropped here.
          .replace(/^KaTeX parse error: /, "")
          // The message quotes the maths it choked on, which for display maths runs
          // over lines, and a reported problem is one line.
          .replace(/\s*\n\s*/g, " ")
          .trim(),
      });
    }
  });

  process.stdout.write(JSON.stringify(rejections));
});
