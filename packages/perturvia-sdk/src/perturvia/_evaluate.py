import logging
from collections.abc import Callable, Iterable
from typing import Any
from uuid import UUID

import httpx

from perturvia import _tracing
from perturvia.evaluation import injection_followed, recovery, tool_errors

logger = logging.getLogger(__name__)

# Bump when a built-in metric changes meaning, so outcomes from different versions are
# never compared as if they measured the same thing.
EVALUATOR_VERSION = 1

Check = Callable[[dict[str, Any]], dict[str, Any]]


def _check_name(check: Check) -> str:
    return getattr(check, "__name__", None) or repr(check)


def _one_line(exc: BaseException) -> str:
    """Format an exception as ExceptionType: first line of its message.

    httpx status errors add a second line with a docs link, and some transport errors
    have no message at all, in which case only the type is returned.
    """
    lines = str(exc).splitlines()
    return f"{type(exc).__name__}: {lines[0]}" if lines else type(exc).__name__


def _run_checks(trace: dict[str, Any], checks: Iterable[Check], outcome: dict[str, Any]) -> None:
    """Merge each check's result into ``outcome``. A failing check is logged and recorded
    in ``outcome["check_errors"]``; the remaining checks still run."""
    errors: list[str] = []
    for check in checks:
        name = _check_name(check)
        try:
            result = check(trace)
            if not isinstance(result, dict):
                raise TypeError(f"returned {type(result).__name__}, expected dict")
        except Exception as exc:
            logger.warning(
                "Perturvia check %s failed on trace %s", name, trace.get("id"), exc_info=True
            )
            errors.append(f"{name}: {_one_line(exc)}")
            continue
        outcome.update(result)
    if errors:
        outcome["check_errors"] = errors


def evaluate(trace_id: UUID | str, checks: Iterable[Check] = ()) -> dict[str, Any] | None:
    """Score a finished trace and store the result as its outcome.

    Fetches the trace, computes the built-in metrics, merges in the dict each check
    returns (a check takes the trace dict), and stores the result with
    ``PUT /v1/traces/{id}/outcome``. Returns the stored outcome.

    A check that raises is recorded in ``outcome["check_errors"]`` and the rest of the
    outcome is still stored. Any other failure is logged and returns None: Perturvia
    never raises into the user's program.
    """
    client = _tracing._client
    if client is None:
        raise RuntimeError("Call perturvia.init() before perturvia.evaluate()")

    path = f"/v1/traces/{trace_id}"
    try:
        response = client.get(path)
        response.raise_for_status()
        trace = response.json()

        outcome: dict[str, Any] = {
            "evaluator_version": EVALUATOR_VERSION,
            "tool_errors": tool_errors(trace["spans"]),
            "recovery": recovery(trace["spans"]),
            "injection_followed": injection_followed(trace),
        }
        _run_checks(trace, checks, outcome)

        response = client.put(f"{path}/outcome", json=outcome)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # Expected: the API is down, slow, or rejected the request. No traceback needed.
        logger.warning("Perturvia evaluation of trace %s failed: %s", trace_id, _one_line(exc))
        return None
    except Exception:
        logger.warning("Perturvia evaluation of trace %s failed", trace_id, exc_info=True)
        return None
    return outcome
