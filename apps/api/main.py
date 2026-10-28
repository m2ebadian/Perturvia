from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentRead

app = FastAPI(title="Perturvia API")


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
