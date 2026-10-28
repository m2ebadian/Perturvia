import os
from functools import cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@cache
def get_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    return create_engine(database_url, echo=False, pool_pre_ping=True)


@cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine())
