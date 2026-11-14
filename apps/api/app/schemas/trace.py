from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

SpanKind = Literal["agent", "llm", "tool"]
SpanStatus = Literal["ok", "error"]


class TraceCreate(BaseModel):
    id: UUID | None = None
    agent_id: UUID | None = None
    task: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    config: dict[str, Any] = Field(default_factory=dict)
    seed: Annotated[int, Field(ge=0, le=2**53 - 1)] | None = None
    experiment_id: UUID | None = None
    trial_number: Annotated[int, Field(ge=1)] | None = None
    started_at: AwareDatetime | None = None


class TraceUpdate(BaseModel):
    status: Literal["completed", "failed"]
    ended_at: AwareDatetime | None = None
    final_output: str | None = None


class TraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_id: UUID | None
    task: str
    status: Literal["running", "completed", "failed"]
    config: dict[str, Any]
    seed: int | None
    experiment_id: UUID | None
    trial_number: int | None
    final_output: str | None
    outcome: dict[str, Any] | None
    started_at: datetime
    ended_at: datetime | None


class SpanCreate(BaseModel):
    id: UUID
    parent_span_id: UUID | None = None
    sequence: Annotated[int, Field(ge=0, le=2**31 - 1)]
    kind: SpanKind
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    agent_name: Annotated[str, StringConstraints(max_length=255)] | None = None
    status: SpanStatus
    error_type: Annotated[str, StringConstraints(max_length=50)] | None = None
    started_at: AwareDatetime
    duration_ms: Annotated[float, Field(ge=0)]
    attributes: dict[str, Any] = Field(default_factory=dict)
    fault: dict[str, Any] | None = None
    retry_of_span_id: UUID | None = None
    input_span_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_error_type(self) -> "SpanCreate":
        if self.status == "ok" and self.error_type is not None:
            raise ValueError("error_type is only allowed when status is 'error'")
        return self


class SpanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    trace_id: UUID
    parent_span_id: UUID | None
    sequence: int
    kind: SpanKind
    name: str
    agent_name: str | None
    status: SpanStatus
    error_type: str | None
    started_at: datetime
    duration_ms: float
    attributes: dict[str, Any]
    fault: dict[str, Any] | None
    retry_of_span_id: UUID | None
    input_span_ids: list[UUID]
    created_at: datetime


class SpanBatch(BaseModel):
    spans: Annotated[list[SpanCreate], Field(min_length=1, max_length=500)]


class TraceDetail(TraceRead):
    spans: list[SpanRead]


class SpanBatchResult(BaseModel):
    received: int
    inserted: int
