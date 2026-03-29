from fastapi import FastAPI, UploadFile, File
import shutil
import os
from app.core.pipelines.auto_insight_pipeline import AutoInsightPipeline
from app.db.insight_store import InsightStore
from app.core.generation.structured_generator import StructuredGenerator
from app.core.ingestion.pipeline import ingest_document
app = FastAPI()


pipeline = AutoInsightPipeline(
    ingestion_pipeline=ingest_document,
    generator=StructuredGenerator(),
    insight_store=InsightStore()
)


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document_id = file.filename

    result = pipeline.run(file_path, document_id)

    os.remove(file_path)

    return {
        "document_id": document_id,
        "insights": result
    }


@app.get("/insights/{document_id}")
def get_insights(document_id: str):
    store = InsightStore()
    data = store.load(document_id)

    if not data:
        return {"error": "Not found"}

    return data