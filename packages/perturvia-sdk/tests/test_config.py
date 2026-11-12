import pytest

from perturvia._config import API_URL_ENV_VAR, DEFAULT_API_URL, resolve_api_url


def test_argument_wins_over_environment(monkeypatch):
    monkeypatch.setenv(API_URL_ENV_VAR, "http://from-env")
    assert resolve_api_url("http://from-arg") == "http://from-arg"


def test_environment_used_when_no_argument(monkeypatch):
    monkeypatch.setenv(API_URL_ENV_VAR, "http://from-env")
    assert resolve_api_url() == "http://from-env"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_default_when_environment_missing_or_empty(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(API_URL_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(API_URL_ENV_VAR, value)
    assert resolve_api_url() == DEFAULT_API_URL


def test_strips_trailing_slash():
    assert resolve_api_url("http://localhost:8000/") == "http://localhost:8000"
