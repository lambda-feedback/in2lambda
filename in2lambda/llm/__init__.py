"""OpenRouter-backed LLM helpers used by ``in2lambda wizard``.

Everything here is part of the optional ``llm`` extra
(``pip install in2lambda[llm]``); importing this package without the extra is
fine, but calling into it raises a clear error.
"""

from in2lambda.llm.client import DEFAULT_MODEL, get_client, resolve_model

__all__ = ["DEFAULT_MODEL", "get_client", "resolve_model"]
