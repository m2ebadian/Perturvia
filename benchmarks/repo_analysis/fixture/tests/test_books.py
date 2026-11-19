def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get_book(client):
    created = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert created.status_code == 201

    book_id = created.json()["id"]
    assert client.get(f"/books/{book_id}").json()["title"] == "Dune"


def test_delete_book(client):
    book_id = client.post("/books", json={"title": "Emma", "author": "Jane Austen"}).json()["id"]

    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
