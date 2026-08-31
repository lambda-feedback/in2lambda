"""Tests for the OpenRouter client factory (the ``llm`` extra).

Everything here is offline: no real client is constructed against the network.
"""

import importlib

import pytest

from in2lambda.llm import client as client_module
from in2lambda.llm.client import DEFAULT_MODEL, get_client, resolve_model


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("IN2LAMBDA_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def test_resolve_model_prefers_cli_value(monkeypatch):
    monkeypatch.setenv("IN2LAMBDA_MODEL", "from/env")
    assert resolve_model("from/cli") == "from/cli"


def test_resolve_model_falls_back_to_env_then_default(monkeypatch):
    assert resolve_model() == DEFAULT_MODEL
    monkeypatch.setenv("IN2LAMBDA_MODEL", "google/gemini-2.0-flash-001")
    assert resolve_model() == "google/gemini-2.0-flash-001"


def test_get_client_without_the_extra_raises(monkeypatch):
    monkeypatch.setattr(client_module, "openai", None)
    with pytest.raises(RuntimeError, match="llm"):
        get_client()


def test_get_client_without_api_key_raises(monkeypatch):
    # dotenv may be absent; if present, stop it loading a real .env during tests.
    if client_module.load_dotenv is not None:
        monkeypatch.setattr(client_module, "load_dotenv", lambda *a, **k: False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        get_client()


@pytest.mark.skipif(
    importlib.util.find_spec("openai") is None, reason="requires the llm extra"
)
def test_get_client_points_at_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    if client_module.load_dotenv is not None:
        monkeypatch.setattr(client_module, "load_dotenv", lambda *a, **k: False)

    client = get_client()

    assert str(client.base_url).rstrip("/") == "https://openrouter.ai/api/v1"
    assert client.api_key == "test-key"
