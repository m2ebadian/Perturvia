from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.dependencies import get_db

app = FastAPI(title="Perturvia API")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Annotated[Session, Depends(get_db)]):
    db.execute(text("SELECT 1")).scalar_one()
    return {"database": "ok"}
