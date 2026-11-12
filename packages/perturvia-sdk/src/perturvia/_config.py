import os

API_URL_ENV_VAR = "PERTURVIA_API_URL"
DEFAULT_API_URL = "http://localhost:8000"


def resolve_api_url(api_url: str | None = None) -> str:
    """Return the API URL from the argument, then the environment, then the default."""
    url = api_url or os.getenv(API_URL_ENV_VAR, "").strip() or DEFAULT_API_URL
    return url.rstrip("/")
