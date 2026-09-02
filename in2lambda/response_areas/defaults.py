"""Type-specific defaults for a response area's ``responseInput.config``.

The stable presentation fields (feedback colours, ``inputSymbols``, ``tests``,
``cases``, ...) live in
``in2lambda/json_convert/minimal_template_response_area.json`` - that template is
the single source for the on-import shape. This module only fills the small
``config`` object, which varies by input type.
"""

_CONFIG_BY_TYPE: dict[str, dict] = {
    "CODE": {"language": "python"},
    "ESSAY": {
        "allowDraw": False,
        "allowScan": False,
        "repeatForSubjects": False,
        "allowEmptySubmission": False,
    },
}


def default_config(response_type: str) -> dict:
    """Return a fresh default ``config`` dict for ``response_type``.

    Unknown types get an empty dict.

    Examples:
        >>> from in2lambda.response_areas.defaults import default_config
        >>> default_config("CODE")
        {'language': 'python'}
        >>> default_config("EXPRESSION")
        {}
    """
    return dict(_CONFIG_BY_TYPE.get(response_type, {}))
