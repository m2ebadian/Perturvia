from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

TraceStatus = Literal["success", "tool_error", "client_exception"]


class ToolTraceCreate(BaseModel):
    run_id: UUID
    agent_id: UUID | None = None
    tool_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    arguments: dict[str, Any]
    result: dict[str, Any] | list[Any] | None = None
    status: TraceStatus
    error_message: str | None = None
    duration_ms: Annotated[float, Field(ge=0)]
    started_at: AwareDatetime


class ToolTraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    run_id: UUID
    agent_id: UUID | None
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | list[Any] | None
    status: TraceStatus
    error_message: str | None
    duration_ms: float
    started_at: datetime
    created_at: datetime
