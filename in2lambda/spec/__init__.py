r"""Reads a spec of selectors, and says what each block of a frozen source is.

A spec is a small YAML file saying which blocks of a document are questions, which are
parts and which are solutions, and which layout they are written in::

    question: Header level=2 text~'^Question'
    part:     Para text~'^\([a-z]\) '
    solution: after Header text=Solutions, label~'^\d+'
    strip:    ['^\([a-z]\) ', '^\d+ ']
    ignore:   Header level=1
    layout:   PartsSepSol

A role is one selector, or a list of them written under it. A block has that role where
any of the role's selectors matches it::

    ignore:
      - Header level=1
      - Para text~'^Marks'

Where a selector cannot say it, a spec names a Python file beside it and calls functions
from it: ``predicates: predicates.py`` and then ``question: Para bold_lead()``, where
``bold_lead`` takes the panflute element and says whether the block is one. The file is
run by :func:`predicates` out of the bytes its caller hashed, so what runs is the file
the draft's log records having run.

Nothing here decides what a question is: the selectors say which blocks are which, and
the layout says how a solution is paired up with the question or part it answers, which
is the one thing that differs between the filters in :mod:`in2lambda.filters` and is
copied from them here. What comes out is one field per question, part and solution, so
that a draft written by a spec says the same things as a draft written by hand.

The same spec runs over every source a draft has frozen. The first is the sheet, laid
out as the layout says; a source after it is a document of solutions written separately,
and its solutions are paired onto the questions of the sheet the way ``in2lambda convert
-a`` pairs an answers file - the ``question`` selector picking out the marker above each
question's solutions rather than a question.

Reading a spec needs pyyaml, which only the ``convert`` extra installs; the command that
calls this checks for it first, along with pandoc and panflute.
"""

import re
import types
from collections.abc import Callable  # Rather than typing's, which beartype warns on.
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple, Optional

from in2lambda.filters import builtin_filters
from in2lambda.source import Block, SourceError, quoted

_KEYS = ("question", "part", "solution", "strip", "ignore", "layout", "predicates")
"""Everything a spec may say. Anything else in one is a typo, and is refused as one."""

_ATTRIBUTES = ("level", "text", "label", "depth")
"""What a constraint can be about.

A heading's level, a block's text, its first word, and how deep the block sits: 1 for a
top-level element of the document, 2 for a block nested inside one. A sheet whose
questions are list items with their parts nested under them is written ``question:
ListItem depth=1`` and ``part: ListItem depth=2``.
"""

_ROLES = ("ignore", "question", "part", "solution")
"""The roles a spec holds selectors for, in the order a block is tried against them.

A block is whatever the first of them to match it says it is. The order is this one
whatever order a spec writes its keys in: ignore before the rest so that a page nobody
wants is out of the way, and question before part so that a question numbered like one
of its own parts is still the question.
"""

_TOKEN = re.compile(
    r"""\s*(?:(?P<name>\w+)\s*(?P<operator>[=~])\s*"""
    r"""(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^\s,]+))"""
    r"""|(?P<predicate>\w+)\(\)|(?P<type>\w+))"""
)
"""One word of a selector: a constraint, a ``predicate()`` call, or a block type.

The call comes before the type, so that ``bold_lead()`` is read as a call rather than as
a type named ``bold_lead`` with a pair of brackets nothing can make anything of.
"""


class BadSpec(SourceError):
    """A spec cannot be read, whether as YAML or as selectors."""


def _refuse(line: int, message: str) -> BadSpec:
    """A refusal of a spec, which always ends by saying which line to go and look at."""
    return BadSpec(f"{message} See line {line} of the spec.")


@dataclass
class Constraint:
    """One ``level=2`` or ``text~'^Question'`` of a selector."""

    attribute: str
    wanted: "re.Pattern[str] | str"

    def holds(self, value: Optional[str]) -> bool:
        """Whether a block's attribute is what this asks for, given the block has one."""
        if value is None:
            return False
        if isinstance(self.wanted, str):
            return value == self.wanted
        return bool(self.wanted.search(value))


@dataclass
class Selector:
    """Which blocks of a document a spec is talking about."""

    type: Optional[str] = None
    constraints: list[Constraint] = field(default_factory=list)
    predicates: list[str] = field(default_factory=list)
    after: Optional["Selector"] = None

    def matches(
        self,
        elements: list[tuple[Block, Any]],
        index: int,
        pf: Any,
        functions: Optional[dict[str, Callable[[Any], Any]]] = None,
    ) -> bool:
        """Whether the block at `index` is one of these.

        Args:
            elements: Every block of the document, each beside the panflute element it
                is. A constraint about ``depth`` is about the block; the rest, and a
                predicate, are about the element.
            index: Which of them to decide about.
            pf: The panflute module, imported by the caller that has it.
            functions: The predicates the spec's file holds, as :func:`predicates` bound
                them, and None where the spec calls none.

        Returns:
            True if the element is of this type, meets every constraint, satisfies every
            predicate it calls, and comes after something the ``after`` selector matches.
        """
        block, element = elements[index]
        if self.after is not None and not any(
            self.after.matches(elements, earlier, pf, functions)
            for earlier in range(index)
        ):
            return False
        if self.type is not None and type(element).__name__ != self.type:
            return False
        if not all(
            constraint.holds(_attribute(constraint.attribute, block, element, pf))
            for constraint in self.constraints
        ):
            return False
        # Last, so that someone's own code only sees the blocks the rest of the selector
        # has already agreed about - a predicate written for a Para is only given one.
        called = functions or {}
        return all(called[name](element) for name in self.predicates)


@dataclass
class Spec:
    """What a spec file says, once it has been read.

    Each role holds one selector or several, and a block has that role where any of them
    matches it. A role a spec leaves out holds none.
    """

    question: list[Selector]
    layout: str
    part: list[Selector] = field(default_factory=list)
    solution: list[Selector] = field(default_factory=list)
    ignore: list[Selector] = field(default_factory=list)
    strip: "list[re.Pattern[str]]" = field(default_factory=list)
    predicates: Optional[str] = None
    """The Python file its selectors call functions from, where any of them do."""


class Field(NamedTuple):
    """One field a spec fills in: what it is called, what it says, where it came from."""

    key: str
    value: str
    ranges: list[list[int]]
    source: int
    """Which of the draft's frozen sources the ranges are lines of, numbered from 1."""


class Doubled(NamedTuple):
    """A block the layout sent to a field another block of the sources had filled in."""

    block: str
    ranges: list[list[int]]
    key: str
    by_block: str
    by_ranges: list[list[int]]
    """Which block the field holds, and the lines that block was taken from."""


def _attribute(name: str, block: Block, element: Any, pf: Any) -> Optional[str]:
    """What a block says for one attribute, or None where it has not got one."""
    if name == "depth":
        return str(block.depth)
    if name == "level":
        return str(element.level) if isinstance(element, pf.Header) else None
    text = pf.stringify(element).strip()
    if name == "text":
        return text
    return words[0] if (words := text.split()) else None


def _split(text: str) -> tuple[str, Optional[str]]:
    """A selector either side of its comma, which a quoted regex may hold its own of."""
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
    """One ``[Type] constraint*`` of a selector, given it says nothing else."""
    selector = Selector(after=after)
    position = 0
    while position < len(text):
        if (token := _TOKEN.match(text, position)) is None:
            raise _refuse(
                line,
                f"{text[position:].strip()!r} is not something a selector says. A "
                "selector is a block type and then any number of name=value or "
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
                    f"{name} is not something a block has: a constraint is about "
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
    """A block type, given pandoc has one of that name."""
    import panflute as pf

    found = getattr(pf, name, None)
    if not (isinstance(found, type) and issubclass(found, pf.Element)):
        raise _refuse(
            line,
            f"{name} is not a pandoc element. A selector names one as pandoc does - "
            "Header, Para, ListItem - or leaves the type out to match any block.",
        )
    return name


def _pattern(regex: Any, line: int) -> "re.Pattern[str]":
    """A regex, given it is one. A backslash in YAML wants single quotes around it."""
    try:
        return re.compile(regex)
    except (re.error, TypeError) as error:  # TypeError: a strip list of numbers.
        raise _refuse(
            line, f"{regex!r} is not a regular expression: {error}."
        ) from None


def _selector(text: Any, line: int) -> Selector:
    """One selector of a spec, as its `after` clause and the rest."""
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
            f"{text!r} has no `after` in it.",
        )
    return _clause(head.strip(), line)


def _selectors(value: Any, line: int, item_lines: list[int]) -> list[Selector]:
    """The selectors of one role: the one written after it, or the list written under it.

    Args:
        value: What the role says, as YAML built it.
        line: Which line the role's key is written on.
        item_lines: Which line each item of the value is written on, where the value is
            a list, so that a refusal names the item rather than the key.
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
    r"""Reads a spec, given that it says what a spec says.

    Args:
        text: The contents of the spec file, as text or as the bytes it was read as.
            The bytes are handed to YAML rather than decoded here, since YAML knows
            which encoding a file is in from its byte order mark and refuses one it
            cannot read the way it refuses anything else about a spec.

    Returns:
        The spec, with its selectors parsed and its strip patterns compiled.

    Raises:
        BadSpec: the text is not YAML, is in an encoding YAML cannot read, is not a
            mapping, says something a spec does not, holds a selector, pattern or layout
            that cannot be read, names a file of predicates that is not beside it, or
            calls a function without naming the file its functions are in. Every one of
            them says which line to look at.

    Examples:
        >>> from in2lambda.spec import load
        >>> load("question: Header level=2\nlayout: PartsOneSol\n").layout
        'PartsOneSol'
    """
    import yaml

    # The composed nodes carry the line each key is written on; the values come from
    # safe_load, which builds them rather than leaving them as nodes to unpick. Both
    # are read here, since a file that composes can still fail to be built - a tag
    # nothing constructs, a key nothing can hash - and that is as much a fault in the
    # spec as a quote left open.
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
    # patterns - a refusal about one item says the line that item is on rather than the
    # line the key is on, which in a list of three is two lines away from the fault.
    items = {
        key.value: [item.start_mark.line + 1 for item in value.value]
        for key, value in node.value
        if isinstance(key, yaml.ScalarNode) and isinstance(value, yaml.SequenceNode)
    }

    # By str, because a key someone has written need not be one: `1: Header` is YAML.
    if unknown := sorted(set(given) - set(_KEYS), key=str):
        raise _refuse(
            lines.get(unknown[0], 1),
            f"{unknown[0]} is not something a spec says. A spec says "
            f"{', '.join(_KEYS)}.",
        )
    if missing := [key for key in ("question", "layout") if key not in given]:
        raise _refuse(
            1,
            "A spec says which blocks are questions and how they are laid out, so it "
            f"has to have a {' and a '.join(missing)} in it.",
        )

    layout = given["layout"]
    if layout not in builtin_filters():
        raise _refuse(
            lines["layout"],
            f"{layout} is not a layout in2lambda has. The layouts are the filters: "
            f"{', '.join(builtin_filters())}.",
        )

    strip = given.get("strip") or []
    if not isinstance(strip, list):
        raise _refuse(
            lines["strip"], f"strip is a list of patterns, which {strip!r} is not."
        )

    file = given.get("predicates")
    # Beside the spec, and so a name with nothing of a path in it. A spec that could
    # name a file anywhere would run and log one the folder it is in does not hold, and
    # the draft would then only replay where that file still sat outside the folder.
    if file is not None and (not isinstance(file, str) or Path(file).name != file):
        raise _refuse(
            lines["predicates"],
            f"predicates names a Python file beside the spec, which {file!r} is not. "
            "The name has no directory in it: the file is in the spec's own folder.",
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
                        f"{called[0]}() is a function, and the spec does not say which "
                        "Python file its functions are in. Put the file beside the spec "
                        "and name it with a predicates: line.",
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
    """Every function a selector calls, its ``after`` clause included."""
    return selector.predicates + (_called(selector.after) if selector.after else [])


def predicates(spec: Spec, code: bytes, name: str) -> dict[str, Callable[[Any], Any]]:
    """The functions a spec's selectors call, out of the file it names.

    Args:
        spec: The spec whose selectors call them, as :func:`load` read it.
        code: What the file holds, as the bytes its caller hashed. The file is run from
            these rather than imported by its path, so that what runs is what was
            checked against the hash the draft's log recorded.
        name: What the file is called, for the traceback of anything it raises and for
            the refusal of anything it has not got.

    Returns:
        One callable per function the spec's selectors name, ready for
        :meth:`Selector.matches`.

    Raises:
        BadSpec: the file holds no function of a name a selector calls, or holds
            something of that name that cannot be called.
    """
    # Run as a module of its own rather than imported by path, so that nothing about
    # where the file is - a name already imported, a stale .pyc - decides what runs.
    module = types.ModuleType("in2lambda_predicates")
    exec(compile(code, name, "exec"), module.__dict__)
    found = {}
    for role in _ROLES:
        for selector in getattr(spec, role):
            for called in _called(selector):
                function = getattr(module, called, None)
                if not callable(function):
                    raise BadSpec(
                        f"{name} has no function {called} in it, and the spec calls "
                        f"{called}(). A predicate is a function of one argument, the "
                        "panflute element, that says whether the block is one of those."
                    )
                found[called] = function
    return found


def _optional(
    given: dict[str, Any],
    name: str,
    lines: dict[str, int],
    items: dict[str, list[int]],
) -> list[Selector]:
    """The selectors of a role a spec need not have, and none where it has not got it."""
    if name not in given:
        return []
    return _selectors(given[name], lines[name], items.get(name, []))


def _stems(roles: list[Optional[str]]) -> list[Optional[str]]:
    """What each question and part is called - ``q1``, ``q1.p1`` - in document order.

    The same names `in2lambda.draft._next` gives out, so that a draft filled in by a spec
    and one filled in by hand hold the same keys, and the checks read either.
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

    Each question with parts is answered part by part; each question without is answered
    itself. That is the order the solutions in a PartsSepSol document are written in, and
    the order a document of solutions written beside the sheet is written in.
    """
    questions: list[tuple[str, list[str]]] = []
    for index, role in enumerate(roles):
        if role == "question":
            questions.append((str(stems[index]), []))
        elif role == "part" and questions and stems[index]:
            questions[-1][1].append(str(stems[index]))
    return [parts or [stem] for stem, parts in questions]


def _keys(layout: str, roles: list[list[Optional[str]]]) -> list[list[Optional[str]]]:
    """The field each block's text goes in, source by source.

    The first source is the sheet, and the layout says which solution written in it
    answers what. Every source after it is a document of solutions written separately
    from the sheet, and is paired onto the sheet's questions rather than laid out.
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
    """The field each block of the sheet goes in, or None where the layout puts it in none."""
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
            # Which solution answers what, mirroring the filter the layout names. The
            # four filters are the four layouts; a fifth would need its rule adding.
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
    """The field each block of a separate document of solutions goes in.

    The pairing `in2lambda convert -a` does, in the words of a spec. A block the
    ``question`` selector matches is a marker - the ``Q2.`` written above the solutions
    to the second question - which answers nothing itself and sends what follows it to
    that question's first slot. Everything else the spec picks out, whether its ``part``
    selector matched or its ``solution`` one, is a solution, and they take the slots in
    order: each question's parts, or the question itself where it has none. A solution
    past the last slot is in no field, and one landing on a question the solutions
    before it have answered is reported by :func:`fields` as doubled.
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
    """What the spec says each block of one source is, or None where it says nothing.

    A block has a role where any one of that role's selectors matches it. A selector
    matches within the source it is run over - ``after Header text=Solutions`` is about
    where a block sits in its own document - so each source is decided about on its own,
    whatever the sources before it hold.

    A block whose children hold a role holds none itself. A parent spans its children,
    so a question quoted from the whole of a list item and a part quoted from an item
    nested inside it would be two fields written over the same lines, which
    `in2lambda.draft.record` refuses. The spec quotes the item's own paragraph into the
    question and the nested items into the parts, and one selector may match both.
    """
    found = [
        next(
            (
                role
                for role in _ROLES
                if any(
                    selector.matches(elements, index, pf, functions)
                    for selector in getattr(spec, role)
                )
            ),
            None,
        )
        for index in range(len(elements))
    ]
    held = {block.id for (block, _), role in zip(elements, found) if role is not None}
    return [
        None if any(other.startswith(f"{block.id}.") for other in held) else role
        for (block, _), role in zip(elements, found)
    ]


def fields(
    spec: Spec,
    documents: list[tuple[list[tuple[Block, Any]], str]],
    functions: Optional[dict[str, Callable[[Any], Any]]] = None,
) -> tuple[list[Field], list[str], list[Doubled]]:
    """What a spec makes of a draft's sources: its fields, and the blocks to ignore.

    Args:
        spec: The spec to run, as :func:`load` read it.
        documents: Every source of the draft, in the order it froze them: each as the
            blocks of its frozen markdown beside the element each is, as
            :func:`in2lambda.source._elements` gives them, and the markdown itself,
            which the values are quoted out of.
        functions: The predicates its selectors call, as :func:`predicates` bound them,
            and None for a spec that calls none.

    Returns:
        One :class:`Field` per question, part and solution the spec found, each saying
        which source it came from; the ids of the blocks to mark as ignored, which are
        what the ``ignore`` selector matched and the markers of a separate document of
        solutions, saying which question the solutions under them answer and nothing
        else; and one :class:`Doubled` per block the layout sent to a field an earlier
        block had filled in. A doubled block is in no field, as a block in neither of
        the first two lists is, which is what a coverage report is about.
    """
    import panflute as pf

    roles = [_roles(spec, elements, pf, functions) for elements, _ in documents]
    written = []
    doubled = []
    # Which block each field was taken from. A layout can send two blocks to the one
    # field - a document of nothing but solutions has more solutions than there are
    # questions to answer - and the second is left in no field, so that the run reports
    # it rather than being refused by `in2lambda.draft.record` and writing nothing.
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
        # A marker is ignored rather than quoted: what it says is which question the
        # solutions under it answer, and that question's text came from the sheet.
        if role == "ignore" or (number > 1 and role == "question")
    ]
    return written, ignored, doubled


def _stripped(spec: Spec, lines: list[str], block: Block) -> str:
    """A block's own lines of the source, with the spec's strip patterns taken off.

    The markdown rather than the text pandoc stringifies it to, so that the maths, the
    emphasis and the images in a question survive into the field.
    """
    # The list marker and the indent under it are the markdown's, not the author's, so
    # they come off before the spec's patterns, which are for what is left.
    text = quoted("\n".join(lines[block.start - 1 : block.end]), block)
    for pattern in spec.strip:
        text = pattern.sub("", text)
    return text.strip()
