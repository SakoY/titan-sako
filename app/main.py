from fastapi import FastAPI

app = FastAPI(title="Open Library Catalog Service")


@app.get("/health")
def health():
    return {"status": "ok"}
