from uuid import UUID


def trace_uuid(trace_id: int) -> UUID:
    """Convert an OpenTelemetry trace ID to a UUID."""
    return UUID(int=trace_id)


def span_uuid(trace_id: int, span_id: int) -> UUID:
    """Convert an OpenTelemetry span ID to a UUID unique within its trace."""
    return UUID(int=((trace_id >> 64) << 64) | span_id)
