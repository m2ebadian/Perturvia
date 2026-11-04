from uuid import UUID

from pydantic import BaseModel


class RunMetricsRead(BaseModel):
    run_id: UUID
    total_calls: int
    successful_calls: int
    tool_errors: int
    client_exceptions: int
    injected_failures: int
    observed_failure_rate: float
    # None when every call was injected: there is no natural behavior to measure.
    natural_failure_rate: float | None
