from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
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
