r"""Reads a spec of selectors, and says what each block of a frozen source is.

A spec is a small YAML file saying which blocks of a document are questions, which are
parts and which are solutions, and which layout the document is written in::

    question: Header level=2 text~'^Question'
    part:     Para text~'^\([a-z]\) '
    solution: after Header text=Solutions, label~'^\d+'
    strip:    ['^\([a-z]\) ', '^\d+ ']
    ignore:   Header level=1
    layout:   PartsSepSol

A role holds one selector, or a list of selectors written under it. A block has that role
where any one of those selectors matches it::

    ignore:
      - Header level=1
      - Para text~'^Marks'

Where no selector can classify a block, a spec names a Python file beside it and calls
functions from that file: ``predicates: predicates.py``, and then ``question: Para
bold_lead()``, where ``bold_lead`` takes the panflute element and returns whether the
block is a question. :func:`predicates` runs the file from the bytes its caller hashed, so
that the file run is the file the draft's log records.

The selectors classify each block as a question, part or solution. The layout assigns each
solution to the question or part it answers, which is the one thing that differs between
the filters in :mod:`in2lambda.filters` and is copied from them here. :func:`fields`
returns one field per question, part and solution, so that a draft written by a spec holds
the fields a draft written by hand holds.

The same spec runs over every source a draft has frozen. The first source is the sheet,
laid out as the layout says. Every source after it is a document of solutions written
separately, and its solutions are paired onto the questions of the sheet as ``in2lambda
convert -a`` pairs an answers file, with the ``question`` selector picking out the marker
above each question's solutions.

Reading a spec needs pyyaml, which only the ``convert`` extra installs. The command
calling this module checks for pyyaml first, along with pandoc and panflute.
"""

import re
import types
from collections.abc import Callable  # Rather than typing's, which beartype warns on.
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple, Optional

from in2lambda.filters import builtin_filters
from in2lambda.source import Block, SourceError, dedented

_KEYS = ("question", "part", "solution", "strip", "ignore", "layout", "predicates")
"""Every key a spec may hold. Any other key is a typo, and is refused as one."""

_ATTRIBUTES = ("level", "text", "label")
"""What a constraint can be about: a heading's level, a block's text, its first word."""

_ROLES = ("ignore", "question", "part", "solution")
"""The roles a spec holds selectors for, in the order each role is matched against a block.

The first selector to match a block classifies that block. This order holds whatever order
a spec writes its keys in: ignore before the other three roles, so that a page of
instructions is classified first, and question before part, so that a question numbered
like one of its own parts is read as a question.
"""

_TOKEN = re.compile(
    r"""\s*(?:(?P<name>\w+)\s*(?P<operator>[=~])\s*"""
    r"""(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^\s,]+))"""
    r"""|(?P<predicate>\w+)\(\)|(?P<type>\w+))"""
)
"""One word of a selector: a constraint, a ``predicate()`` call, or a block type.

The call comes before the type, so that ``bold_lead()`` is read as a call and not as a
type named ``bold_lead`` followed by brackets the parser cannot read.
"""


class BadSpec(SourceError):
    """A spec cannot be read, whether as YAML or as selectors."""


def _refuse(line: int, message: str) -> BadSpec:
    """A refusal of a spec, which ends by naming the line to read."""
    return BadSpec(f"{message} See line {line} of the spec.")


@dataclass
class Constraint:
    """One ``level=2`` or ``text~'^Question'`` of a selector."""

    attribute: str
    wanted: "re.Pattern[str] | str"

    def holds(self, value: Optional[str]) -> bool:
        """Whether a block's attribute matches, which is False where it has none."""
        if value is None:
            return False
        if isinstance(self.wanted, str):
            return value == self.wanted
        return bool(self.wanted.search(value))


@dataclass
class Selector:
    """The blocks of a document that one key of a spec selects."""

    type: Optional[str] = None
    constraints: list[Constraint] = field(default_factory=list)
    predicates: list[str] = field(default_factory=list)
    after: Optional["Selector"] = None

    def matches(
        self,
        elements: list[Any],
        index: int,
        pf: Any,
        functions: Optional[dict[str, Callable[[Any], Any]]] = None,
    ) -> bool:
        """Whether the block at `index` matches this selector.

        Args:
            elements: Every block of the document, as the panflute element it is.
            index: Which block to test.
            pf: The panflute module, imported by the caller that holds it.
            functions: The predicates the spec's file holds, as :func:`predicates` bound
                them, and None where the spec calls none.

        Returns:
            True where the element is of this type, meets every constraint, satisfies
            every predicate it calls, and follows a block the ``after`` selector matches.
        """
        element = elements[index]
        if self.after is not None and not any(
            self.after.matches(elements, earlier, pf, functions)
            for earlier in range(index)
        ):
            return False
        if self.type is not None and type(element).__name__ != self.type:
            return False
        if not all(
            constraint.holds(_attribute(constraint.attribute, element, pf))
            for constraint in self.constraints
        ):
            return False
        # Last, so that a reader's own code is given only the blocks the rest of the
        # selector matched: a predicate written for a Para is given a Para.
        called = functions or {}
        return all(called[name](element) for name in self.predicates)


@dataclass
class Spec:
    """The keys a spec file holds, once :func:`load` has read them.

    Each role holds one selector or several, and a block has that role where any one of
    those selectors matches the block. A role a spec omits holds no selector.
    """

    question: list[Selector]
    layout: str
    part: list[Selector] = field(default_factory=list)
    solution: list[Selector] = field(default_factory=list)
    ignore: list[Selector] = field(default_factory=list)
    strip: "list[re.Pattern[str]]" = field(default_factory=list)
    predicates: Optional[str] = None
    """The Python file its selectors call functions from, where any selector does."""


class Field(NamedTuple):
    """One field a spec fills in: its key, its value, and the lines it came from."""

    key: str
    value: str
    ranges: list[list[int]]
    source: int
    """Which of the draft's frozen sources the ranges are lines of, numbered from 1."""


class Doubled(NamedTuple):
    """A block the layout assigns to a field an earlier block of the sources filled in."""

    block: str
    ranges: list[list[int]]
    key: str
    by_block: str
    by_ranges: list[list[int]]
    """Which block the field holds, and the lines that block was taken from."""


def _attribute(name: str, element: Any, pf: Any) -> Optional[str]:
    """What a block holds for one attribute, or None where the block holds none."""
    if name == "level":
        return str(element.level) if isinstance(element, pf.Header) else None
    text = pf.stringify(element).strip()
    if name == "text":
        return text
    return words[0] if (words := text.split()) else None


def _split(text: str) -> tuple[str, Optional[str]]:
    """A selector's text either side of its comma, ignoring commas inside quotes."""
    quote = ""
    for position, character in enumerate(text):
        if quote:
            if character == quote:
                quote = ""
        elif character in "\"'":
            quote = character
        elif character == ",":
            return text[:position], text[position + 1 :]
    return text, None


def _clause(text: str, line: int, after: Optional[Selector] = None) -> Selector:
    """One ``[Type] constraint*`` of a selector, where the text says nothing else."""
    selector = Selector(after=after)
    position = 0
    while position < len(text):
        if (token := _TOKEN.match(text, position)) is None:
            raise _refuse(
                line,
                f"{text[position:].strip()!r} is not something a selector holds. A "
                "selector is a block type followed by any number of name=value or "
                "name~'regex' constraints.",
            )
        position = token.end()
        if (called := token["predicate"]) is not None:
            selector.predicates.append(called)
        elif (name := token["name"]) is None:
            if selector.type is not None or selector.constraints:
                raise _refuse(
                    line,
                    "A selector names one block type, before its constraints, so "
                    f"{token['type']} is one word too many.",
                )
            selector.type = _type(token["type"], line)
        else:
            if name not in _ATTRIBUTES:
                raise _refuse(
                    line,
                    f"{name} is not an attribute a block holds: a constraint names "
                    f"{', '.join(_ATTRIBUTES)}.",
                )
            wanted = next(
                value
                for value in (token["double"], token["single"], token["bare"])
                if value is not None
            )
            selector.constraints.append(
                Constraint(
                    name, _pattern(wanted, line) if token["operator"] == "~" else wanted
                )
            )
    return selector


def _type(name: str, line: int) -> str:
    """A block type, where pandoc holds an element of that name."""
    import panflute as pf

    found = getattr(pf, name, None)
    if not (isinstance(found, type) and issubclass(found, pf.Element)):
        raise _refuse(
            line,
            f"{name} is not a pandoc element. A selector names an element as pandoc "
            "does - Header, Para, ListItem - or omits the type to match any block.",
        )
    return name


def _pattern(regex: Any, line: int) -> "re.Pattern[str]":
    """A regex, where the value is one. A backslash in YAML needs single quotes."""
    try:
        return re.compile(regex)
    except (re.error, TypeError) as error:  # TypeError: a strip list of numbers.
        raise _refuse(
            line, f"{regex!r} is not a regular expression: {error}."
        ) from None


def _selector(text: Any, line: int) -> Selector:
    """One selector of a spec, split into its `after` clause and the rest."""
    if not isinstance(text, str):
        raise _refuse(line, f"A selector is a line of text, which {text!r} is not.")
    head, tail = _split(text.strip())
    if head.strip().startswith("after "):
        after = _clause(head.strip()[len("after ") :], line)
        return _clause(tail.strip() if tail else "", line, after)
    if tail is not None:
        raise _refuse(
            line,
            "A selector's comma separates its `after` clause from the rest, and "
            f"{text!r} holds no `after` clause.",
        )
    return _clause(head.strip(), line)


def _selectors(value: Any, line: int, item_lines: list[int]) -> list[Selector]:
    """The selectors of one role: the selector written after the key, or the list under it.

    Args:
        value: The role's value, as YAML built it.
        line: Which line the role's key is written on.
        item_lines: Which line each item of the value is written on, where the value is
            a list, so that a refusal names the item and not the key.
    """
    if not isinstance(value, list):
        return [_selector(value, line)]
    if not value:
        raise _refuse(
            line,
            "A role is a selector or a list of selectors, which an empty list is not.",
        )
    return [
        _selector(item, item_lines[index] if index < len(item_lines) else line)
        for index, item in enumerate(value)
    ]


def load(text: "str | bytes") -> Spec:
    r"""Reads a spec from the YAML text of a spec file.

    Args:
        text: The contents of the spec file, as text or as the bytes it was read as. The
            bytes are passed to YAML undecoded, because YAML reads a file's encoding from
            its byte order mark and refuses an encoding it cannot read as it refuses
            anything else about a spec.

    Returns:
        The spec, with its selectors parsed and its strip patterns compiled.

    Raises:
        BadSpec: the text is not YAML, is in an encoding YAML cannot read, is not a
            mapping, holds a key a spec does not hold, holds a selector, pattern or
            layout this module cannot read, names a file of predicates that is not beside
            it, or calls a function without naming the file holding it. Every message
            names the line to read.

    Examples:
        >>> from in2lambda.spec import load
        >>> load("question: Header level=2\nlayout: PartsOneSol\n").layout
        'PartsOneSol'
    """
    import yaml

    # The composed nodes record the line each key is written on, and safe_load builds the
    # values, which the nodes leave to be unpicked. Both run here, because a file that
    # composes can still fail to build - a tag nothing constructs, a key nothing can hash
    # - and that is a fault in the spec as much as a quote left open is.
    try:
        node = yaml.compose(text)
        given = yaml.safe_load(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        raise _refuse(
            1 if mark is None else mark.line + 1, f"The spec is not YAML: {error}."
        ) from None

    if not isinstance(node, yaml.MappingNode):
        raise _refuse(1, "A spec is a mapping of question, part, solution and so on.")
    lines = {
        key.value: key.start_mark.line + 1
        for key, _ in node.value
        if isinstance(key, yaml.ScalarNode)
    }
    # Where a value is a list - a role written as several selectors, a strip of several
    # patterns - a refusal about one item names the line that item is written on. The
    # key's own line is up to two lines away from the fault in a list of three.
    items = {
        key.value: [item.start_mark.line + 1 for item in value.value]
        for key, value in node.value
        if isinstance(key, yaml.ScalarNode) and isinstance(value, yaml.SequenceNode)
    }

    # Sorted by str, because a key a reader wrote need not be one: `1: Header` is YAML.
    if unknown := sorted(set(given) - set(_KEYS), key=str):
        raise _refuse(
            lines.get(unknown[0], 1),
            f"{unknown[0]} is not a key a spec holds. A spec holds "
            f"{', '.join(_KEYS)}.",
        )
    if missing := [key for key in ("question", "layout") if key not in given]:
        raise _refuse(
            1,
            "A spec says which blocks are questions and how the solutions are laid out, "
            f"so it must hold a {' and a '.join(missing)}.",
        )

    layout = given["layout"]
    if layout not in builtin_filters():
        raise _refuse(
            lines["layout"],
            f"{layout} is not a layout in2lambda holds. The layouts are the filters: "
            f"{', '.join(builtin_filters())}.",
        )

    strip = given.get("strip") or []
    if not isinstance(strip, list):
        raise _refuse(
            lines["strip"], f"strip is a list of patterns, which {strip!r} is not."
        )

    file = given.get("predicates")
    # Beside the spec, so the name holds no path. A spec free to name a file anywhere
    # would run and log a file the spec's own folder does not hold, and the draft would
    # then replay only where that file still sat outside the folder.
    if file is not None and (not isinstance(file, str) or Path(file).name != file):
        raise _refuse(
            lines["predicates"],
            f"predicates names a Python file beside the spec, which {file!r} is not. "
            "The name holds no directory: the file is in the spec's own folder.",
        )
    question = _selectors(
        given["question"], lines["question"], items.get("question", [])
    )
    rest = {
        role: _optional(given, role, lines, items)
        for role in _ROLES
        if role != "question"
    }
    if file is None:
        for role, selectors in {"question": question, **rest}.items():
            for selector in selectors:
                if called := _called(selector):
                    raise _refuse(
                        lines[role],
                        f"{called[0]}() is a function, and the spec does not name the "
                        "Python file holding its functions. Put the file beside the "
                        "spec and name it with a predicates: line.",
                    )
    strip_lines = items.get("strip", [])
    return Spec(
        question=question,
        layout=layout,
        part=rest["part"],
        solution=rest["solution"],
        ignore=rest["ignore"],
        strip=[
            _pattern(
                pattern,
                strip_lines[index] if index < len(strip_lines) else lines["strip"],
            )
            for index, pattern in enumerate(strip)
        ],
        predicates=file,
    )


def _called(selector: Selector) -> list[str]:
    """Every function a selector calls, including the calls in its ``after`` clause."""
    return selector.predicates + (_called(selector.after) if selector.after else [])


def predicates(spec: Spec, code: bytes, name: str) -> dict[str, Callable[[Any], Any]]:
    """The functions a spec's selectors call, from the file the spec names.

    Args:
        spec: The spec whose selectors call them, as :func:`load` read it.
        code: The contents of the file, as the bytes its caller hashed. The file is run
            from those bytes and not imported by its path, so that the code run is the
            code checked against the hash the draft's log records.
        name: The file's name, for the traceback of anything it raises and for the
            message naming a function it does not hold.

    Returns:
        One callable per function the spec's selectors name, for
        :meth:`Selector.matches`.

    Raises:
        BadSpec: the file holds no function of a name a selector calls, or holds
            something of that name that cannot be called.
    """
    # Run as a module of its own and not imported by path, so that nothing about the
    # file's location - a name already imported, a stale .pyc - decides what runs.
    module = types.ModuleType("in2lambda_predicates")
    exec(compile(code, name, "exec"), module.__dict__)
    found = {}
    for role in _ROLES:
        for selector in getattr(spec, role):
            for called in _called(selector):
                function = getattr(module, called, None)
                if not callable(function):
                    raise BadSpec(
                        f"{name} holds no function {called}, and the spec calls "
                        f"{called}(). A predicate is a function of one argument, the "
                        "panflute element, that returns whether the selector matches."
                    )
                found[called] = function
    return found


def _optional(
    given: dict[str, Any],
    name: str,
    lines: dict[str, int],
    items: dict[str, list[int]],
) -> list[Selector]:
    """The selectors of a role a spec need not hold, and none for a role it omits."""
    if name not in given:
        return []
    return _selectors(given[name], lines[name], items.get(name, []))


def _stems(roles: list[Optional[str]]) -> list[Optional[str]]:
    """The name of each question and part - ``q1``, ``q1.p1`` - in document order.

    `in2lambda.draft._next` gives out the same names, so that a draft filled in by a spec
    and a draft filled in by hand hold the same keys, and the checks read either.
    """
    stems: list[Optional[str]] = [None] * len(roles)
    questions, parts = 0, 0
    for index, role in enumerate(roles):
        if role == "question":
            questions, parts = questions + 1, 0
            stems[index] = f"q{questions}"
        elif role == "part" and questions:
            parts += 1
            stems[index] = f"q{questions}.p{parts}"
    return stems


def _slots(roles: list[Optional[str]], stems: list[Optional[str]]) -> list[list[str]]:
    """What a separate section of solutions answers, question by question.

    A question with parts is answered part by part, and a question without parts is
    answered itself. The solutions of a PartsSepSol document are written in that order,
    as are the solutions of a document written beside the sheet.
    """
    questions: list[tuple[str, list[str]]] = []
    for index, role in enumerate(roles):
        if role == "question":
            questions.append((str(stems[index]), []))
        elif role == "part" and questions and stems[index]:
            questions[-1][1].append(str(stems[index]))
    return [parts or [stem] for stem, parts in questions]


def _keys(layout: str, roles: list[list[Optional[str]]]) -> list[list[Optional[str]]]:
    """The field key each block's text is written to, source by source.

    The first source is the sheet, and the layout says which solution written in it
    answers what. Every source after it is a document of solutions written separately
    from the sheet, and its solutions are paired onto the sheet's questions.
    """
    stems = _stems(roles[0])
    slots = _slots(roles[0], stems)
    return [_laid_out(layout, roles[0], stems, slots)] + [
        _answers(later, slots) for later in roles[1:]
    ]


def _laid_out(
    layout: str,
    roles: list[Optional[str]],
    stems: list[Optional[str]],
    slots: list[list[str]],
) -> list[Optional[str]]:
    """The field key each block of the sheet is written to, or None for no field."""
    separate = iter([slot for question in slots for slot in question])
    keys: list[Optional[str]] = [None] * len(roles)
    question: Optional[str] = None
    parts: list[str] = []
    answered = 0
    for index, role in enumerate(roles):
        if role == "question":
            question, parts, answered = stems[index], [], 0
            keys[index] = f"{question}.text"
        elif role == "part" and stems[index]:
            parts.append(str(stems[index]))
            keys[index] = f"{stems[index]}.text"
        elif role == "solution" and question:
            # Which solution answers what, as the filter the layout names does. The four
            # filters are the four layouts, and a fifth layout needs its rule added here.
            target: Optional[str]
            match layout:
                case "PartsOneSol":  # One solution to the whole question.
                    target = question
                case "PartSolPartSol":  # Each part answered where it stands.
                    target = parts[-1] if parts else question
                case "PartPartSolSol":  # The parts, then their solutions in order.
                    target = parts[answered] if answered < len(parts) else question
                case _:  # PartsSepSol: every solution together, at the end.
                    target = next(separate, None)
            answered += 1
            keys[index] = f"{target}.solution" if target else None
    return keys


def _answers(roles: list[Optional[str]], slots: list[list[str]]) -> list[Optional[str]]:
    """The field key each block of a separate document of solutions is written to.

    `in2lambda convert -a` pairs an answers file this way. A block the ``question``
    selector matches is a marker - the ``Q2.`` written above the solutions to the second
    question - which answers nothing and assigns the blocks after it to that question's
    first slot. Every other block the spec matched, by its ``part`` selector or by its
    ``solution`` selector, is a solution, and the solutions take the slots in order: each
    question's parts, or the question itself where it has no parts. A solution past the
    last slot is in no field. A solution assigned to a question that an earlier solution
    answered is reported by :func:`fields` as doubled.
    """
    ordered = [
        (number, slot) for number, question in enumerate(slots) for slot in question
    ]
    keys: list[Optional[str]] = [None] * len(roles)
    at, markers = 0, 0
    for index, role in enumerate(roles):
        if role == "question":
            markers += 1
            at = next(
                (
                    position
                    for position, (number, _) in enumerate(ordered)
                    if number == markers - 1
                ),
                len(ordered),
            )
        elif role in ("part", "solution") and at < len(ordered):
            keys[index] = f"{ordered[at][1]}.solution"
            at += 1
    return keys


def _roles(
    spec: Spec,
    elements: list[tuple[Block, Any]],
    pf: Any,
    functions: Optional[dict[str, Callable[[Any], Any]]],
) -> list[Optional[str]]:
    """The role each block of one source matches: question, part, solution, or None.

    A block has a role where any one of that role's selectors matches it. A selector
    matches within the source it is run over - ``after Header text=Solutions`` names a
    position in one document - so each source is classified on its own, whatever the
    sources before it hold.
    """
    found = [element for _, element in elements]
    return [
        next(
            (
                role
                for role in _ROLES
                if any(
                    selector.matches(found, index, pf, functions)
                    for selector in getattr(spec, role)
                )
            ),
            None,
        )
        for index in range(len(found))
    ]


def fields(
    spec: Spec,
    documents: list[tuple[list[tuple[Block, Any]], str]],
    functions: Optional[dict[str, Callable[[Any], Any]]] = None,
) -> tuple[list[Field], list[str], list[Doubled]]:
    """The fields a spec writes from a draft's sources, and the blocks in no field.

    Args:
        spec: The spec to run, as :func:`load` read it.
        documents: Every source of the draft, in the order it froze them: each as the
            blocks of its frozen markdown beside the element of each, as
            :func:`in2lambda.source._elements` returns them, and the markdown the values
            are quoted out of.
        functions: The predicates its selectors call, as :func:`predicates` bound them,
            and None for a spec that calls none.

    Returns:
        One :class:`Field` per question, part and solution the spec matched, each naming
        the source it came from; the ids of the blocks to mark as ignored, which are the
        blocks the ``ignore`` selector matched and the markers of a separate document of
        solutions, which name the question the solutions under them answer; and one
        :class:`Doubled` per block the layout sent to a field an earlier block had filled
        in. A doubled block is in no field, and so is a block in neither of the first two
        lists. `in2lambda.draft.report.uncovered` reports both.
    """
    import panflute as pf

    roles = [_roles(spec, elements, pf, functions) for elements, _ in documents]
    written = []
    doubled = []
    # Which block each field was taken from. A layout can assign two blocks to one field
    # - a document of nothing but solutions holds more solutions than the layout has
    # questions to answer - and the second block is left in no field, so that the run
    # reports that block instead of `in2lambda.draft.record` refusing the whole run.
    holders: dict[str, tuple[str, list[list[int]]]] = {}
    for number, ((elements, markdown), keys) in enumerate(
        zip(documents, _keys(spec.layout, roles)), start=1
    ):
        lines = markdown.splitlines()
        for (block, _), key in zip(elements, keys):
            if key is None:
                continue
            ranges = [[block.start, block.end]]
            if key in holders:
                by_block, by_ranges = holders[key]
                doubled.append(Doubled(block.id, ranges, key, by_block, by_ranges))
                continue
            holders[key] = (block.id, ranges)
            written.append(Field(key, _stripped(spec, lines, block), ranges, number))
    ignored = [
        block.id
        for number, ((elements, _), found) in enumerate(zip(documents, roles), start=1)
        for (block, _), role in zip(elements, found)
        # A marker is ignored and not quoted: it names the question the solutions under
        # it answer, and that question's text was copied from the sheet.
        if role == "ignore" or (number > 1 and role == "question")
    ]
    return written, ignored, doubled


def _stripped(spec: Spec, lines: list[str], block: Block) -> str:
    """A block's own lines of the source, with the spec's strip patterns removed.

    The value is the markdown, and not the text pandoc stringifies it to, so that the
    maths, the emphasis and the images of a question survive into the field.
    """
    text = "\n".join(lines[block.start - 1 : block.end])
    # The list marker and the indent under it belong to the markdown and not to the
    # author, so they come off before the spec's patterns, which are for the rest.
    if block.type == "list item":
        text = dedented(text)
    for pattern in spec.strip:
        text = pattern.sub("", text)
    return text.strip()
