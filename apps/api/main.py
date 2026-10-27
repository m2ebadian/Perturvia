from fastapi import FastAPI

app = FastAPI(title="Perturvia API")


@app.get("/health")
def health_check():
    return {"status": "ok"}
