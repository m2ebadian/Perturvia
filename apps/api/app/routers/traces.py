from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.trace import Span, Trace
from app.schemas.trace import (
    SpanBatch,
    SpanBatchResult,
    TraceCreate,
    TraceDetail,
    TraceRead,
    TraceUpdate,
)

router = APIRouter(prefix="/v1/traces", tags=["traces"])


def _constraint_name(exc: IntegrityError) -> str | None:
    """Return the name of the database constraint that caused ``exc``, if known."""
    return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)


@router.post("", response_model=TraceRead, status_code=201)
def create_trace(trace: TraceCreate, db: Annotated[Session, Depends(get_db)]):
    new_trace = Trace(**trace.model_dump(exclude_none=True))
    db.add(new_trace)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = _constraint_name(exc)
        if constraint == "fk_traces_agent_id_agents":
            raise HTTPException(status_code=422, detail="Agent not found") from exc
        if constraint == "traces_pkey":
            raise HTTPException(status_code=409, detail="Trace already exists") from exc
        raise

    db.refresh(new_trace)

    return new_trace


@router.post("/{trace_id}/spans", response_model=SpanBatchResult, status_code=201)
def ingest_spans(trace_id: UUID, batch: SpanBatch, db: Annotated[Session, Depends(get_db)]):
    rows = [{**span.model_dump(), "trace_id": trace_id} for span in batch.spans]
    stmt = (
        insert(Span).values(rows).on_conflict_do_nothing(index_elements=["id"]).returning(Span.id)
    )

    try:
        inserted_ids = db.scalars(stmt).all()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        constraint = _constraint_name(exc)
        if constraint == "fk_spans_trace_id_traces":
            raise HTTPException(status_code=404, detail="Trace not found") from exc
        if constraint == "uq_spans_trace_id_sequence":
            raise HTTPException(status_code=409, detail="Duplicate span sequence") from exc
        raise

    return SpanBatchResult(received=len(batch.spans), inserted=len(inserted_ids))


@router.patch("/{trace_id}", response_model=TraceRead)
def finish_trace(trace_id: UUID, update: TraceUpdate, db: Annotated[Session, Depends(get_db)]):
    trace = db.get(Trace, trace_id, with_for_update=True)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    if trace.status != "running":
        raise HTTPException(status_code=409, detail="Trace is already finished")

    trace.status = update.status
    trace.final_output = update.final_output
    trace.ended_at = update.ended_at or datetime.now(UTC)

    db.commit()
    db.refresh(trace)

    return trace


@router.get("", response_model=list[TraceRead])
def list_traces(
    db: Annotated[Session, Depends(get_db)],
    agent_id: UUID | None = None,
    experiment_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    query = select(Trace)
    if agent_id is not None:
        query = query.where(Trace.agent_id == agent_id)
    if experiment_id is not None:
        query = query.where(Trace.experiment_id == experiment_id)
    query = query.order_by(Trace.started_at.desc(), Trace.id.desc()).limit(limit)
    return db.scalars(query).all()


@router.get("/{trace_id}", response_model=TraceDetail)
def get_trace(trace_id: UUID, db: Annotated[Session, Depends(get_db)]):
    trace = db.get(Trace, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
