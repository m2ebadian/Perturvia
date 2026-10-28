from app.database.session import get_session_factory


def get_db():
    session_factory = get_session_factory()
    db = session_factory()

    try:
        yield db
    finally:
        db.close()
