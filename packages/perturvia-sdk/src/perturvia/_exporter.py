import json
import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import httpx
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

from perturvia._ids import span_uuid, trace_uuid

logger = logging.getLogger(__name__)

_NS_PER_SECOND = 1_000_000_000
_NS_PER_MS = 1_000_000
_PREFIX = "perturvia."
_KINDS = frozenset({"agent", "llm", "tool"})
_MAX_SPANS_PER_REQUEST = 500


def _parse_fault(raw: object) -> dict | None:
    """Parse a fault attribute from JSON, returning None if it is missing or invalid."""
    if not isinstance(raw, str):
        return None
    try:
        fault = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return fault if isinstance(fault, dict) else None


def span_to_payload(span: ReadableSpan) -> dict | None:
    """Convert a finished OpenTelemetry span into a Perturvia span payload.

    Returns None for spans that cannot produce a valid payload, so one bad span
    never causes the API to reject the whole batch.
    """
    trace_id = span.context.trace_id
    attrs = span.attributes or {}

    sequence = attrs.get(f"{_PREFIX}sequence")
    if sequence is None:
        logger.warning("Skipping span %r: missing %ssequence", span.name, _PREFIX)
        return None

    parent_span_id = None
    if span.parent is not None:
        parent_span_id = str(span_uuid(trace_id, span.parent.span_id))

    status = "error" if span.status.status_code == StatusCode.ERROR else "ok"

    kind = attrs.get(f"{_PREFIX}kind")
    if kind not in _KINDS:
        kind = "agent"

    return {
        "id": str(span_uuid(trace_id, span.context.span_id)),
        "parent_span_id": parent_span_id,
        "name": span.name,
        "started_at": datetime.fromtimestamp(span.start_time / _NS_PER_SECOND, UTC).isoformat(),
        "duration_ms": (span.end_time - span.start_time) / _NS_PER_MS,
        "status": status,
        "kind": kind,
        "sequence": sequence,
        "agent_name": attrs.get(f"{_PREFIX}agent_name"),
        "error_type": attrs.get(f"{_PREFIX}error_type") if status == "error" else None,
        "fault": _parse_fault(attrs.get(f"{_PREFIX}fault")),
        "retry_of_span_id": attrs.get(f"{_PREFIX}retry_of_span_id"),
        "input_span_ids": list(attrs.get(f"{_PREFIX}input_span_ids", [])),
        "attributes": {k: v for k, v in attrs.items() if not k.startswith(_PREFIX)},
    }


class PerturviaSpanExporter(SpanExporter):
    """Sends finished spans to the Perturvia API, one request per trace chunk.

    export() never raises: it runs on OpenTelemetry's background thread, and
    telemetry failures must never break the agent being traced.
    """

    def __init__(self, api_url: str, timeout: float = 5.0) -> None:
        self._api_url = api_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            groups: defaultdict[UUID, list[dict]] = defaultdict(list)
            for span in spans:
                payload = span_to_payload(span)
                if payload is not None:
                    groups[trace_uuid(span.context.trace_id)].append(payload)

            ok = True
            for trace_id, payloads in groups.items():
                url = f"{self._api_url}/v1/traces/{trace_id}/spans"
                for start in range(0, len(payloads), _MAX_SPANS_PER_REQUEST):
                    chunk = payloads[start : start + _MAX_SPANS_PER_REQUEST]
                    if not self._send(url, chunk):
                        ok = False
            return SpanExportResult.SUCCESS if ok else SpanExportResult.FAILURE
        except Exception:
            logger.warning("Perturvia span export failed unexpectedly", exc_info=True)
            return SpanExportResult.FAILURE

    def _send(self, url: str, chunk: list[dict]) -> bool:
        """POST one chunk of spans. Returns False on any network or HTTP error."""
        try:
            response = self._client.post(url, json={"spans": chunk})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to send %d spans to %s: %s", len(chunk), url, exc)
            return False
        return True

    def shutdown(self) -> None:
        self._client.close()
