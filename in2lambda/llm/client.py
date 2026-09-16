"""Build an OpenAI-compatible client pointed at OpenRouter.

Configuration is read from the environment (a local ``.env`` file is loaded if
one is present):

* ``OPENROUTER_API_KEY`` - required; create one at https://openrouter.ai/keys.
* ``IN2LAMBDA_MODEL``    - optional; the model slug to use when none is passed
  on the command line. Defaults to :data:`DEFAULT_MODEL`.
"""

import os
from typing import Optional

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - provided by the `llm` extra
    find_dotenv = None
    load_dotenv = None

try:
    import openai
except ImportError:  # pragma: no cover - provided by the `llm` extra
    openai = None

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# A cheap, widely-available default. Override per run with --model or the
# IN2LAMBDA_MODEL environment variable; any OpenRouter model slug works.
DEFAULT_MODEL = "openai/gpt-4o-mini"

_INSTALL_HINT = (
    "in2lambda's LLM features need the 'llm' extra: pip install 'in2lambda[llm]'"
)


def resolve_model(cli_value: Optional[str] = None) -> str:
    """Return the model slug to use.

    Precedence: an explicit CLI value, then ``$IN2LAMBDA_MODEL``, then
    :data:`DEFAULT_MODEL`.

    Args:
        cli_value: The value passed via ``--model``, if any.

    Returns:
        An OpenRouter model slug.

    Examples:
        >>> from in2lambda.llm.client import resolve_model
        >>> resolve_model("anthropic/claude-3.5-haiku")
        'anthropic/claude-3.5-haiku'
    """
    return cli_value or os.getenv("IN2LAMBDA_MODEL") or DEFAULT_MODEL


def get_client() -> "openai.OpenAI":
    """Return an OpenAI client configured to talk to OpenRouter.

    Raises:
        RuntimeError: if the ``llm`` extra is not installed, or
            ``OPENROUTER_API_KEY`` is not set.
    """
    if openai is None:
        raise RuntimeError(_INSTALL_HINT)

    if load_dotenv is not None:
        # find_dotenv()'s default search starts from the calling module's
        # file location, which is inside site-packages once installed. Use
        # usecwd=True so it searches from the user's project directory.
        load_dotenv(find_dotenv(usecwd=True))

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Create a key at "
            "https://openrouter.ai/keys and put it in your environment or a "
            ".env file."
        )

    return openai.OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
