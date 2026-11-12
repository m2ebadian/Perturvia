import logging
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import INVALID_SPAN, Span, Status, StatusCode, Tracer

from perturvia._config import resolve_api_url
from perturvia._exporter import _KINDS, _PREFIX, PerturviaSpanExporter
from perturvia._ids import span_uuid, trace_uuid
from perturvia._processor import SequenceProcessor

logger = logging.getLogger(__name__)

_MAX_NAME_LENGTH = 255
_MAX_ERROR_TYPE_LENGTH = 50

_provider: TracerProvider | None = None
_tracer: Tracer | None = None
_api_url: str | None = None
_client: httpx.Client | None = None
_timeout: float = 5.0


def init(api_url: str | None = None, *, timeout: float = 5.0) -> None:
    """Configure Perturvia tracing. Calling it again replaces the previous setup."""
    global _provider, _tracer, _api_url, _client, _timeout

    if _provider is not None:
        _provider.shutdown()
    if _client is not None:
        _client.close()

    url = resolve_api_url(api_url)

    provider = TracerProvider()
    provider.add_span_processor(SequenceProcessor())
    provider.add_span_processor(BatchSpanProcessor(PerturviaSpanExporter(url, timeout)))

    _provider = provider
    _tracer = provider.get_tracer("perturvia")
    _api_url = url
    _client = httpx.Client(base_url=url, timeout=timeout)
    _timeout = timeout


@dataclass
class Run:
    """Handle for an active run. Set ``final_output`` before the block ends."""

    trace_id: UUID
    final_output: str | None = None


# The run active in the current thread or async task, so span() knows whether to trace.
_active_run: ContextVar[Run | None] = ContextVar("perturvia_active_run", default=None)
_warned_no_run = False


def _request(method: str, path: str, payload: dict[str, Any]) -> bool:
    """Send one API request. Perturvia failures are logged, never raised.

    This is the boundary between Perturvia and the user's program, so it catches
    everything, including serialization errors raised before any network call.
    """
    assert _client is not None
    try:
        response = _client.request(method, path, json=payload)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Perturvia %s %s failed: %s", method, path, exc)
        return False
    return True


def _flush() -> None:
    assert _provider is not None
    try:
        _provider.force_flush(timeout_millis=int(_timeout * 1000))
    except Exception:
        logger.warning("Perturvia span flush failed", exc_info=True)


@contextmanager
def run(
    task: str,
    *,
    agent_id: UUID | str | None = None,
    config: dict[str, Any] | None = None,
    seed: int | None = None,
    experiment_id: UUID | str | None = None,
    trial_number: int | None = None,
) -> Generator[Run, None, None]:
    """Trace one agent run: creates the trace, yields a Run, then finishes the trace.

    Exceptions from the user's code are recorded on the trace and re-raised.
    Failures talking to Perturvia are logged and never interrupt the agent.
    """
    if _tracer is None or _provider is None or _client is None:
        raise RuntimeError("Call perturvia.init() before perturvia.run()")

    status = "failed"
    created = False
    current: Run | None = None
    try:
        # Records the exception and sets ERROR status on the root span if the body raises,
        # then ends the span. The exception itself keeps propagating.
        with _tracer.start_as_current_span("run") as root:
            trace_id = trace_uuid(root.get_span_context().trace_id)
            fields = {
                "id": str(trace_id),
                "task": task,
                "agent_id": str(agent_id) if agent_id is not None else None,
                "config": config,
                "seed": seed,
                "experiment_id": str(experiment_id) if experiment_id is not None else None,
                "trial_number": trial_number,
            }
            created = _request(
                "POST", "/v1/traces", {k: v for k, v in fields.items() if v is not None}
            )

            current = Run(trace_id=trace_id)
            token = _active_run.set(current)
            try:
                yield current
            except Exception as exc:
                error_type = type(exc).__name__[:_MAX_ERROR_TYPE_LENGTH]
                root.set_attribute(f"{_PREFIX}error_type", error_type)
                raise
            finally:
                _active_run.reset(token)
            status = "completed"
    finally:
        if created and current is not None:
            ended_at = datetime.now(UTC).isoformat()
            final_output = current.final_output
            if final_output is not None and not isinstance(final_output, str):
                # A text version beats a PATCH that fails and leaves the trace "running".
                final_output = str(final_output)
            _flush()
            _request(
                "PATCH",
                f"/v1/traces/{current.trace_id}",
                {"status": status, "ended_at": ended_at, "final_output": final_output},
            )


def mark_error(span: Span, error_type: str, description: str | None = None) -> None:
    """Mark a span as failed without raising, e.g. a tool error returned to the model.

    Sets ERROR status and the error type (truncated to the API's limit). Safe to call
    on the non-recording span that span() yields outside a run: it does nothing.
    """
    span.set_status(Status(StatusCode.ERROR, description))
    span.set_attribute(f"{_PREFIX}error_type", error_type[:_MAX_ERROR_TYPE_LENGTH])


@contextmanager
def span(
    name: str,
    *,
    kind: str = "agent",
    agent_name: str | None = None,
    retry_of: Span | None = None,
) -> Generator[Span, None, None]:
    """Trace one agent, LLM or tool step inside a run.

    Yields the OpenTelemetry span, so callers can set extra attributes on it or
    pass it as ``retry_of`` to a later span. Invalid arguments raise ValueError
    immediately: they are programming mistakes, not runtime failures.

    Outside a run() it yields a non-recording span and sends nothing, so code
    that uses span() still works when called on its own, for example in tests.
    """
    global _warned_no_run
    if _tracer is None:
        raise RuntimeError("Call perturvia.init() before perturvia.span()")
    if not name.strip() or len(name) > _MAX_NAME_LENGTH:
        raise ValueError(f"span name must be 1-{_MAX_NAME_LENGTH} characters")
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {sorted(_KINDS)}, got {kind!r}")
    if agent_name is not None and len(agent_name) > _MAX_NAME_LENGTH:
        raise ValueError(f"agent_name must be at most {_MAX_NAME_LENGTH} characters")

    if _active_run.get() is None:
        if not _warned_no_run:
            logger.warning("perturvia.span() called outside perturvia.run(); not tracing it")
            _warned_no_run = True
        yield INVALID_SPAN
        return

    attributes: dict[str, str] = {f"{_PREFIX}kind": kind}
    if agent_name is not None:
        attributes[f"{_PREFIX}agent_name"] = agent_name
    if retry_of is not None:
        ctx = retry_of.get_span_context()
        attributes[f"{_PREFIX}retry_of_span_id"] = str(span_uuid(ctx.trace_id, ctx.span_id))

    with _tracer.start_as_current_span(name, attributes=attributes) as current:
        try:
            yield current
        except Exception as exc:
            error_type = type(exc).__name__[:_MAX_ERROR_TYPE_LENGTH]
            current.set_attribute(f"{_PREFIX}error_type", error_type)
            raise
