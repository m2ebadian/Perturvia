import threading

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

SEQUENCE_ATTRIBUTE = "perturvia.sequence"


class SequenceProcessor(SpanProcessor):
    """Numbers spans in the order they start, separately for each trace."""

    def __init__(self) -> None:
        self._counters: dict[int, int] = {}
        self._lock = threading.Lock()

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        trace_id = span.context.trace_id
        with self._lock:
            n = self._counters.get(trace_id, 0)
            self._counters[trace_id] = n + 1
        span.set_attribute(SEQUENCE_ATTRIBUTE, n)

    def on_end(self, span: ReadableSpan) -> None:
        if span.parent is None or span.parent.is_remote:
            with self._lock:
                self._counters.pop(span.context.trace_id, None)
