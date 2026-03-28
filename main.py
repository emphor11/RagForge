from fastapi import FastAPI

app = FastAPI(title="RAGForge v2")


@app.get("/")
def root():
    return {"message": "RAGForge v2 is running"}