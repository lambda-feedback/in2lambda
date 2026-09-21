"""What `in2lambda.compare` folds out before comparing, and what it reports.

`test_against_convert` compares two real sets with these functions. The sets here are
built in the test, one field apart, so that each normalisation is covered on its own.
"""

from pathlib import Path

from click.testing import CliRunner
from conftest import EXPORTS_DIR

from in2lambda.api.part import Part
from in2lambda.api.set import Set
from in2lambda.compare import differences, known
from in2lambda.main import cli

_EXPORT = str(EXPORTS_DIR / "me2_introduction")
"""A real export, compared with itself by the command-line tests."""


def _set(main_text: str = "", *parts: tuple[str, str]) -> Set:
    """One question holding `main_text` and a part per (text, worked solution) pair."""
    question_set = Set()
    question_set.add_question(main_text=main_text)
    for text, worked_solution in parts:
        question_set.current_question.parts.append(
            Part(text=text, worked_solution=worked_solution)
        )
    return question_set


def test_a_run_of_whitespace_is_one_space() -> None:
    """A field wrapped over two lines says what the same field on one line says."""
    assert (
        differences(_set("The piston\nis  large."), _set("The piston is large.")) == []
    )


def test_an_image_is_compared_by_the_file_name() -> None:
    """The alt text and the directory differ between the routes; the file name does not."""
    assert (
        differences(_set("![fig](figures/a.png)"), _set("![pictureTag](a.png)")) == []
    )

    assert differences(_set("![fig](figures/a.png)"), _set("![pictureTag](b.png)")) == [
        "Question 1 \"\", main text: the draft says '![](a.png)' and convert says "
        "'![](b.png)'"
    ]


def test_a_lone_empty_part_is_dropped() -> None:
    """A question exported as one empty part matches a question written with no part."""
    assert differences(_set("Find the load.", ("", "")), _set("Find the load.")) == []

    assert differences(
        _set("Find the load.", ("", ""), ("", "")), _set("Find the load.")
    ) == [
        'Question 1 "", part (a): the draft wrote this part and convert did not',
        'Question 1 "", part (b): the draft wrote this part and convert did not',
    ]


def test_a_difference_names_the_question_the_part_and_the_field() -> None:
    """Each line quotes what both sets say, under the names the arguments give."""
    built = _set("Find the load.", ("State the pressure.", "$F = pA$"))
    expected = _set("Find the load.", ("State the pressure.", "$F = 2pA$"))

    assert differences(built, expected) == [
        "Question 1 \"\", part (a), worked solution: the draft says '$F = pA$' and "
        "convert says '$F = 2pA$'"
    ]
    assert differences(built, expected, "set.zip", "the export") == [
        "Question 1 \"\", part (a), worked solution: set.zip says '$F = pA$' and "
        "the export says '$F = 2pA$'"
    ]


def test_known_reads_the_lines_without_their_tickets(tmp_path: Path) -> None:
    """A differs.txt names the differences two sets have; a missing file names none."""
    path = tmp_path / "differs.txt"
    path.write_text(
        "Question 1 \"\", main text: the draft says 'a' and convert says 'b'  # t12\n"
        "\n"
        'Question 2 "": convert wrote this question and the draft did not  # t13\n'
    )

    assert known(path) == [
        "Question 1 \"\", main text: the draft says 'a' and convert says 'b'",
        'Question 2 "": convert wrote this question and the draft did not',
    ]
    assert known(tmp_path / "no_such_file.txt") == []


def test_a_known_difference_is_the_difference_found(tmp_path: Path) -> None:
    """The one difference between two sets is the line a differs.txt holds for them."""
    path = tmp_path / "differs.txt"
    path.write_text(
        "Question 1 \"\", main text: the draft says 'Find the load.' and convert says "
        "'Find the force.'  # t99\n"
    )

    assert differences(_set("Find the load."), _set("Find the force.")) == known(path)


def test_the_command_reports_a_set_compared_with_itself_as_identical() -> None:
    """`in2lambda compare` on one export twice finds nothing to report, and exits 0."""
    result = CliRunner().invoke(cli, ["compare", _EXPORT, _EXPORT])

    assert result.exit_code == 0, result.output
    assert "Identical." in result.output


def test_the_command_refuses_a_known_difference_that_is_not_there(
    tmp_path: Path,
) -> None:
    """A line of the --known file that the comparison does not find is a failure."""
    path = tmp_path / "differs.txt"
    path.write_text("Question 1 \"\", main text: the export says 'a'  # t99\n")

    result = CliRunner().invoke(
        cli, ["compare", _EXPORT, _EXPORT, "--known", str(path)]
    )

    assert result.exit_code == 1
    assert "Not found: Question 1 \"\", main text: the export says 'a'" in result.output


def test_the_command_prints_each_difference_between_two_sets(tmp_path: Path) -> None:
    """Two sets that differ are reported line by line, and the command exits 1."""
    built = tmp_path / "built"
    _set("Find the load.").to_json(str(built))
    expected = tmp_path / "expected"
    _set("Find the force.").to_json(str(expected))

    result = CliRunner().invoke(
        cli, ["compare", str(built / "set"), str(expected / "set")]
    )

    assert result.exit_code == 1
    assert "Find the load." in result.output and "Find the force." in result.output
