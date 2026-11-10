from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Trace(Base):
    __tablename__ = "traces"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_traces_status",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("uuidv7()"))
    agent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL", name="fk_traces_agent_id_agents"),
        nullable=True,
        index=True,
    )
    task: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'running'"))
    config: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    experiment_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    trial_number: Mapped[int | None] = mapped_column(nullable=True)
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Span(Base):
    __tablename__ = "spans"
    __table_args__ = (
        CheckConstraint("kind IN ('agent', 'llm', 'tool')", name="ck_spans_kind"),
        CheckConstraint("status IN ('ok', 'error')", name="ck_spans_status"),
        CheckConstraint("status = 'error' OR error_type IS NULL", name="ck_spans_error_type"),
        UniqueConstraint("trace_id", "sequence", name="uq_spans_trace_id_sequence"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("uuidv7()"))
    trace_id: Mapped[UUID] = mapped_column(
        ForeignKey("traces.id", ondelete="CASCADE", name="fk_spans_trace_id_traces")
    )
    parent_span_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    sequence: Mapped[int] = mapped_column()
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float] = mapped_column()
    attributes: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    fault: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retry_of_span_id: Mapped[UUID | None] = mapped_column(nullable=True)
    input_span_ids: Mapped[list[UUID]] = mapped_column(ARRAY(Uuid), server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
