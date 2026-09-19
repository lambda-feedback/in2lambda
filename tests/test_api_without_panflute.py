"""The Python API authors and exports a set without panflute installed.

panflute is only in the ``convert`` extra. The test runs in a fresh interpreter
with panflute blocked, so a module-level import anywhere on the API path fails it
even though the development environment has panflute.
"""

import json
import subprocess
import sys

SCRIPT = """
import sys
sys.modules["panflute"] = None  # makes `import panflute` raise ImportError

from in2lambda.api.set import Set

s = Set()
s.add_question("Q", "text")
s.current_question.add_part_text("part a")
s.current_question.add_solution("solution a")
s.to_json(sys.argv[1])
"""


def test_api_works_without_panflute(tmp_path) -> None:
    """A set with a part and a solution is written to JSON without panflute."""
    subprocess.run([sys.executable, "-c", SCRIPT, str(tmp_path)], check=True)

    question = json.loads((tmp_path / "set" / "question_000_Q.json").read_text())
    assert question["title"] == "Q"
    assert len(question["parts"]) == 1
