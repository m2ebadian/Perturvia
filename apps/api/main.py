from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import false, func, not_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.agent import Agent, ToolTrace
from app.routers import traces
from app.schemas.agent import AgentCreate, AgentRead
from app.schemas.run_metrics import RunMetricsRead
from app.schemas.tool_trace import ToolTraceCreate, ToolTraceRead

app = FastAPI(title="Perturvia API")
app.include_router(traces.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Annotated[Session, Depends(get_db)]):
    db.execute(text("SELECT 1")).scalar_one()
    return {"database": "ok"}


@app.post("/agents", response_model=AgentRead, status_code=201)
def create_agent(agent: AgentCreate, db: Annotated[Session, Depends(get_db)]):
    new_agent = Agent(name=agent.name, description=agent.description)
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return new_agent


@app.get("/agents", response_model=list[AgentRead])
def read_agents(db: Annotated[Session, Depends(get_db)]):
    query = select(Agent).order_by(Agent.created_at.desc(), Agent.id.desc())
    agents = db.scalars(query).all()
    return agents


@app.get("/agents/{agent_id}", response_model=AgentRead)
def read_agent(agent_id: UUID, db: Annotated[Session, Depends(get_db)]):
    agent = db.get(Agent, agent_id)

    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@app.post("/traces", response_model=ToolTraceRead, status_code=201)
def create_trace(trace: ToolTraceCreate, db: Annotated[Session, Depends(get_db)]):
    new_trace = ToolTrace(**trace.model_dump())
    db.add(new_trace)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Let PostgreSQL enforce the foreign key; a pre-insert lookup could race with a delete.
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "fk_tool_traces_agent_id_agents":
            raise HTTPException(status_code=422, detail="Agent not found") from exc
        raise

    db.refresh(new_trace)

    return new_trace


@app.get("/traces", response_model=list[ToolTraceRead])
def read_traces(db: Annotated[Session, Depends(get_db)], run_id: UUID):
    query = (
        select(ToolTrace)
        .where(ToolTrace.run_id == run_id)
        .order_by(ToolTrace.started_at.asc(), ToolTrace.id.asc())
    )
    traces = db.scalars(query).all()
    return traces


@app.get("/runs/{run_id}/metrics", response_model=RunMetricsRead)
def read_run_metrics(run_id: UUID, db: Annotated[Session, Depends(get_db)]):
    # @> is NULL when fault_injection is NULL; coalesce so NOT(injected) still counts those rows.
    injected = func.coalesce(
        ToolTrace.fault_injection.contains({"failure_injected": True}), false()
    )
    query = select(
        func.count().label("total_calls"),
        func.count().filter(ToolTrace.status == "success").label("successful_calls"),
        func.count().filter(ToolTrace.status == "tool_error").label("tool_errors"),
        func.count().filter(ToolTrace.status == "client_exception").label("client_exceptions"),
        func.count().filter(injected).label("injected_failures"),
        func.count()
        .filter(ToolTrace.status != "success", not_(injected))
        .label("natural_failures"),
    ).where(ToolTrace.run_id == run_id)
    counts = db.execute(query).one()

    if counts.total_calls == 0:
        raise HTTPException(status_code=404, detail="Run not found")

    non_injected_calls = counts.total_calls - counts.injected_failures

    return RunMetricsRead(
        run_id=run_id,
        total_calls=counts.total_calls,
        successful_calls=counts.successful_calls,
        tool_errors=counts.tool_errors,
        client_exceptions=counts.client_exceptions,
        injected_failures=counts.injected_failures,
        observed_failure_rate=(counts.total_calls - counts.successful_calls) / counts.total_calls,
        natural_failure_rate=(
            counts.natural_failures / non_injected_calls if non_injected_calls else None
        ),
    )
