"""Subject specific panflute filters for parsing LaTeX documents."""

import pkgutil


def builtin_filters() -> list[str]:
    """Lists the filters shipped with in2lambda.

    Each filter is a subpackage of this one; ``markdown`` is a helper module they share.

    Returns:
        The filter names, as accepted by :func:`in2lambda.main.runner`.

    Examples:
        >>> from in2lambda.filters import builtin_filters
        >>> "PartsSepSol" in builtin_filters()
        True
    """
    return [i.name for i in pkgutil.iter_modules(__path__) if i.name != "markdown"]
