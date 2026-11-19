from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/books", tags=["books"])


class BookIn(BaseModel):
    title: str
    author: str


class Book(BookIn):
    id: int


BOOKS: dict[int, Book] = {}


@router.get("")
def list_books() -> list[Book]:
    return list(BOOKS.values())


@router.get("/{book_id}")
def get_book(book_id: int) -> Book:
    if book_id not in BOOKS:
        raise HTTPException(status_code=404, detail="Book not found")
    return BOOKS[book_id]


@router.post("", status_code=201)
def create_book(book: BookIn) -> Book:
    new = Book(id=max(BOOKS, default=0) + 1, **book.model_dump())
    BOOKS[new.id] = new
    return new


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int) -> None:
    if BOOKS.pop(book_id, None) is None:
        raise HTTPException(status_code=404, detail="Book not found")
