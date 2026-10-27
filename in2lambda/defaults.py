"""The defaults in2lambda writes for settings left unset, kept in ``defaults.toml``."""

import copy
import re
import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any, Optional

from beartype.door import is_bearable

from in2lambda.api.visibility_status import VisibilityController, VisibilityStatus


class _Unset:
    def __repr__(self) -> str:
        return "<default>"


UNSET: Any = _Unset()
"""Marks a field whose value comes from the defaults."""

_DEFAULTS = tomllib.loads(Path(__file__).with_name("defaults.toml").read_text())


def _key(name: str) -> str:
    """A field's key in the defaults, e.g. ``_chatbotVisibility`` -> ``chatbot_visibility``."""
    return re.sub(r"(?<!^)([A-Z])", r"_\1", name.lstrip("_")).lower()


def override(path: str) -> None:
    """Replaces in2lambda's defaults with those set in a TOML file.

    The file is laid out as in2lambda's own ``defaults.toml`` and need hold only the
    values to change. Objects created afterwards take the new defaults.

    Args:
        path: The TOML file.

    Raises:
        ValueError: The file is not valid TOML, or sets something in2lambda has no
            default for, or a value of the wrong type. The defaults are then left as they were.
    """
    from in2lambda.api.question import Question
    from in2lambda.api.response_area import RESPONSE_TYPES, ResponseArea
    from in2lambda.api.set import Set

    classes: dict[str, Any] = {
        "set": Set,
        "question": Question,
        "response_area": ResponseArea,
    }
    try:
        new = tomllib.loads(Path(path).read_text())
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path} is not valid TOML: {error}") from error
    # Changed on a copy, so that a file with a mistake in it changes nothing.
    staged = copy.deepcopy(_DEFAULTS)
    for section, values in new.items():
        if section not in classes:
            raise ValueError(f"{path}: in2lambda has no defaults for [{section}]")
        for key, value in values.items():
            if section == "response_area" and isinstance(value, dict):
                if key not in RESPONSE_TYPES:
                    raise ValueError(f"{path}: there is no response type {key}")
                _check(path, RESPONSE_TYPES[key], value)
                staged[section].setdefault(key, {}).update(value)
            else:
                _check(path, classes[section], {key: value})
                staged[section][key] = value
    _DEFAULTS.clear()
    _DEFAULTS.update(staged)


def _check(path: str, cls: Any, values: dict[str, Any]) -> None:
    settable = {_key(f.name): f.type for f in fields(cls) if f.default is UNSET}
    for key, value in values.items():
        if key not in settable:
            raise ValueError(f"{path}: {cls.__name__} has no default {key}")
        if settable[key] is VisibilityController:
            VisibilityStatus(value)
        elif not is_bearable(value, settable[key]):
            raise ValueError(f"{path}: {key} = {value!r} is not a {settable[key]}")


def fill(obj: Any, section: str, response_type: Optional[str] = None) -> None:
    """Sets each of an object's unset fields to its default.

    Args:
        obj: A dataclass instance.
        section: Its table in the defaults.
        response_type: For a response area, its type, whose own table comes first.

    Raises:
        TypeError: A field has no default, or the defaults give it a value of the
            wrong type.
    """
    general = _DEFAULTS[section]
    specific = general.get(response_type, {}) if response_type else {}
    for f in fields(obj):
        if getattr(obj, f.name) is not UNSET:
            continue
        key = _key(f.name)
        if key in specific:
            value = specific[key]
        elif key in general and not isinstance(general[key], dict):
            value = general[key]
        else:
            raise TypeError(f"{type(obj).__name__} needs a value for {f.name}")
        if f.type is VisibilityController:
            value = VisibilityController(VisibilityStatus(value))
        elif not is_bearable(value, f.type):
            raise TypeError(
                f"the default {section} {key} = {value!r} is not a {f.type}"
            )
        setattr(obj, f.name, copy.deepcopy(value))
