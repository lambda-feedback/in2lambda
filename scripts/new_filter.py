#!/usr/bin/env python3

"""Scaffold a new in2lambda filter package.

Creates ``in2lambda/filters/<Name>/`` with an ``__init__.py``, a ``filter.py``
skeleton and an example document, following the layout of the built-in filters.
The new filter is picked up automatically by ``in2lambda convert`` - there is no
registry to edit.

Usage::

    python scripts/new_filter.py <Name> [--md] [--repo-root PATH]

``<Name>`` is the filter name as it appears on the command line (case-insensitive
there, but CapWords is the convention). Pass ``--md`` when the filter parses
markdown rather than LaTeX, so an ``example.md`` is created instead of an
``example.tex``.

This script only uses the standard library; it does not import in2lambda. See
``docs/source/contributing/writing-a-filter.md`` for the full walkthrough.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

TEMPLATE_DIR = Path(__file__).resolve().parent / "filter_template"
NAME_TOKEN = "__FILTER_NAME__"
KIND_TOKEN = "__EXAMPLE_KIND__"


def find_repo_root(start: Path) -> Path:
    """Return the nearest ancestor of ``start`` that contains ``pyproject.toml``."""
    for directory in (start, *start.parents):
        if (directory / "pyproject.toml").is_file():
            return directory
    raise SystemExit(
        "Could not find the repository root (no pyproject.toml in any parent "
        "directory). Pass --repo-root explicitly."
    )


def render(template: Path, name: str, is_markdown: bool) -> str:
    """Fill the placeholder tokens in ``template`` for filter ``name``."""
    text = template.read_text(encoding="utf-8")
    text = text.replace(NAME_TOKEN, name)
    text = text.replace(KIND_TOKEN, "markdown" if is_markdown else "TeX")
    return text


def main(argv: Optional[list[str]] = None) -> None:
    """Parse arguments and write the new filter package."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("name", help="Filter name, e.g. PartsSepSol (CapWords).")
    parser.add_argument(
        "--md",
        action="store_true",
        help="Create example.md instead of example.tex (markdown filter).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to the in2lambda repository root (default: found automatically).",
    )
    args = parser.parse_args(argv)

    name: str = args.name
    if not name.isidentifier():
        raise SystemExit(
            f"{name!r} is not a valid Python identifier - the name has to work "
            "as a package directory."
        )
    if name == "markdown":
        raise SystemExit("'markdown' is reserved for the shared helper module.")

    repo_root = (args.repo_root or find_repo_root(Path.cwd())).resolve()
    filters_dir = repo_root / "in2lambda" / "filters"
    if not filters_dir.is_dir():
        raise SystemExit(f"{filters_dir} does not exist - is --repo-root correct?")

    target = filters_dir / name
    if target.exists():
        raise SystemExit(f"{target} already exists.")

    example_name = "example.md" if args.md else "example.tex"
    example_template = "example.md.tmpl" if args.md else "example.tex.tmpl"
    files = {
        "__init__.py": TEMPLATE_DIR / "__init__.py.tmpl",
        "filter.py": TEMPLATE_DIR / "filter.py.tmpl",
        example_name: TEMPLATE_DIR / example_template,
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing template file(s):\n  " + "\n  ".join(missing))

    target.mkdir(parents=True)
    for out_name, template in files.items():
        (target / out_name).write_text(
            render(template, name, args.md), encoding="utf-8"
        )

    rel = target.relative_to(repo_root)
    print(f"Created {rel}/")
    for out_name in files:
        print(f"  {rel}/{out_name}")
    print(
        "\nNext steps:\n"
        f"  1. Edit {rel}/{example_name} down to the smallest document showing "
        "your structure.\n"
        f"  2. Implement pandoc_filter in {rel}/filter.py and write its module "
        "docstring.\n"
        f'  3. Add "{name}" to BUILTIN_FILTERS in tests/test_runner.py.\n'
        f"  4. Try it:  poetry run in2lambda convert {rel}/{example_name} {name} "
        "-o ./out\n"
        "  5. Run:     poetry run pytest && poetry run pre-commit run --all-files\n"
        "\nGuide: docs/source/contributing/writing-a-filter.md"
    )


if __name__ == "__main__":
    main()
