"""Root pytest config: skip modules that need the optional ``llm`` extra when it is absent.

CI installs ``--all-extras`` so everything runs there; this only keeps
``pytest --doctest-modules`` working on a bare ``poetry install``.
"""

try:
    import pydantic  # noqa: F401
except ImportError:  # pragma: no cover
    collect_ignore = [
        "in2lambda/wizard/extract.py",
        "in2lambda/wizard/run.py",
        "in2lambda/wizard/confirm.py",
    ]
