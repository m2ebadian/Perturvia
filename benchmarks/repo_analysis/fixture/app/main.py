from fastapi import FastAPI
from pydantic_settings import BaseSettings

from app.routers import books


class Settings(BaseSettings):
    app_name: str = "Bookshelf"


settings = Settings()
app = FastAPI(title=settings.app_name)
app.include_router(books.router)


@app.get("/")
def root():
    return {"app": settings.app_name}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    return {"book_count": len(books.BOOKS)}


# Removed in v0.2: search moved to the client.
# @app.get("/search")
# def search(q: str):
#     return [b for b in books.BOOKS.values() if q.lower() in b.title.lower()]
