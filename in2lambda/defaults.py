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
