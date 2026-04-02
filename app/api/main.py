from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from app.core.pipelines.auto_insight_pipeline import AutoInsightPipeline
from app.db.insight_store import InsightStore
from app.core.generation.structured_generator import StructuredGenerator
from app.core.ingestion.pipeline import ingest_document
from app.evaluation.evaluator import InsightEvaluator
from app.core.retrieval.vector_retriever import VectorRetriever
from app.core.retrieval.bm25_retriever import BM25Retriever
from app.core.retrieval.hybrid_retriever import HybridRetriever
from app.core.reranking.reranker import Reranker
from app.db.chroma_store import ChromaStore
from app.core.review.legal_query import select_contract_query_docs

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_generation_ready(generator: StructuredGenerator):
    if not getattr(generator, "api_key", None):
        raise HTTPException(
            status_code=503,
            detail="Generation is not configured. Set GROQ_API_KEY before using this endpoint."
        )


@app.get("/")
def root():
    return {"status": "ok", "version": "2.0", "message": "RAGForge v2 Engine"}


pipeline = AutoInsightPipeline(
    ingestion_pipeline=ingest_document,
    generator=StructuredGenerator(),
    insight_store=InsightStore(),
    evaluator=InsightEvaluator()
)


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    ensure_generation_ready(pipeline.generator)

    file_path = f"temp_{file.filename}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        document_id = file.filename
        result = pipeline.run(file_path, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to upload and analyze document."
        ) from exc
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    return {
        "document_id": document_id,
        "insights": result.get("insights"),
        "evaluation": result.get("evaluation")
    }


@app.get("/documents")
def list_documents():
    store = InsightStore()
    return store.list_all()


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    store = InsightStore()
    data = store.load(document_id)
    if not data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove from insights DB
    path = os.path.join(store.base_path, f"{document_id}.json")
    if os.path.exists(path):
        os.remove(path)
        
    # Remove from Vector DB
    chroma = ChromaStore()
    chroma.collection.delete(where={"source": document_id})
    return {"message": "Document deleted successfully"}


@app.get("/insights/{document_id}")
def get_insights(document_id: str):
    store = InsightStore()
    data = store.load(document_id)

    if not data:
        return {"error": "Not found"}

    return data


@app.get("/contracts/{document_id}/overview")
def get_contract_overview(document_id: str):
    store = InsightStore()
    data = store.load(document_id)

    if not data:
        raise HTTPException(status_code=404, detail="Contract not found")

    contract_profile = data.get("contract_profile")
    if not contract_profile:
        raise HTTPException(
            status_code=404,
            detail="Contract profile not available for this document yet."
        )

    return contract_profile


@app.get("/contracts/{document_id}/clauses")
def get_contract_clauses(document_id: str):
    store = InsightStore()
    data = store.load(document_id)

    if not data:
        raise HTTPException(status_code=404, detail="Contract not found")

    contract_profile = data.get("contract_profile")
    if not contract_profile:
        raise HTTPException(
            status_code=404,
            detail="Contract profile not available for this document yet."
        )

    clauses = data.get("clauses")
    if clauses is None:
        clauses = contract_profile.get("clause_index", [])

    return {
        "document_id": document_id,
        "clauses": clauses,
        "count": len(clauses),
    }


@app.get("/contracts/{document_id}/risks")
def get_contract_risks(document_id: str):
    store = InsightStore()
    data = store.load(document_id)

    if not data:
        raise HTTPException(status_code=404, detail="Contract not found")

    review_findings = data.get("review_findings", [])

    return {
        "document_id": document_id,
        "findings": review_findings,
        "count": len(review_findings),
    }


@app.get("/contracts/{document_id}/review-audit")
def get_contract_review_audit(document_id: str):
    store = InsightStore()
    data = store.load(document_id)

    if not data:
        raise HTTPException(status_code=404, detail="Contract not found")

    review_audit = data.get("review_audit")
    if not review_audit:
        raise HTTPException(
            status_code=404,
            detail="Contract review audit is not available for this document yet."
        )

    return review_audit


@app.get("/reports")
def get_reports():
    store = InsightStore()
    docs = store.list_all()
    
    report_data = {
        "total_docs": len(docs),
        "total_risks": 0,
        "total_actions": 0,
        "risk_summary": {"high": 0, "medium": 0, "low": 0},
        "top_insights": [],
        "doc_list": []
    }
    
    unique_insights = set()
    
    for doc in docs:
        full_data = store.load(doc["id"])
        if not full_data:
            continue
            
        # Support both new nested format and legacy top-level format
        details = full_data.get("insights") if "insights" in full_data else full_data
            
        # Aggregate risks
        risks = details.get("risks", [])
        report_data["total_risks"] += len(risks)
        for risk in risks:
            severity = risk.get("severity", "low").lower()
            if severity in report_data["risk_summary"]:
                report_data["risk_summary"][severity] += 1
                
        # Aggregate actions
        actions = details.get("recommended_actions", [])
        report_data["total_actions"] += len(actions)
        
        # Collect insights
        insights = details.get("key_insights", [])
        for insight in insights:
            insight_text = insight.get("insight") if isinstance(insight, dict) else insight
            if insight_text and insight_text not in unique_insights:
                unique_insights.add(insight_text)
                if len(report_data["top_insights"]) < 10:
                    report_data["top_insights"].append(insight_text)
                    
        # Document brief for list
        report_data["doc_list"].append({
            "name": doc["id"],
            "summary": details.get("summary", "No summary available.")
        })
            
    return report_data


@app.get("/analytics")
def get_analytics():
    from datetime import datetime, timedelta
    store = InsightStore()
    docs = store.list_all()
    
    analytics = {
        "docs_over_time": {},
        "risk_trend": {"last_week": 0, "this_week": 0, "direction": "stable"},
        "performance": {"avg_confidence": 0.0, "avg_response_time": 2.1},
        "usage": {"total_queries": 0, "total_analyses": len(docs)}
    }
    
    total_conf = 0
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    
    for doc in docs:
        full_data = store.load(doc["id"])
        if not full_data:
            continue
            
        # Date aggregation
        dt = datetime.fromtimestamp(doc["upload_date"])
        date_str = dt.strftime("%Y-%m-%d")
        analytics["docs_over_time"][date_str] = analytics["docs_over_time"].get(date_str, 0) + 1

        # Support both new nested format and legacy top-level format
        details = full_data.get("insights") if "insights" in full_data else full_data
            
        # Confidence
        conf = details.get("overall_confidence") or details.get("confidence_score") or 0.0
        total_conf += conf
        
        # Risk trend calculation
        risks_count = len(details.get("risks", []))
        if dt > one_week_ago:
            analytics["risk_trend"]["this_week"] += risks_count
        else:
            analytics["risk_trend"]["last_week"] += risks_count

    # Final calculations
    if len(docs) > 0:
        analytics["performance"]["avg_confidence"] = round(total_conf / len(docs), 2)
        
    # Trend direction
    if analytics["risk_trend"]["this_week"] < analytics["risk_trend"]["last_week"]:
        analytics["risk_trend"]["direction"] = "down"
    elif analytics["risk_trend"]["this_week"] > analytics["risk_trend"]["last_week"]:
        analytics["risk_trend"]["direction"] = "up"
    
    # Mocking untracked query counts for the UI demo/simple version
    analytics["usage"]["total_queries"] = len(docs) * 4 
    
    return analytics


class QueryRequest(BaseModel):
    query: str
    document_id: Optional[str] = None


class FindingStatusUpdate(BaseModel):
    status: str


class FindingNoteUpdate(BaseModel):
    reviewer_note: str


@app.post("/query")
def query_api(request: QueryRequest):
    query = request.query
    document_id = request.document_id
    insight_store = InsightStore()
    stored_contract = insight_store.load(document_id) if document_id else None

    contract_query_docs = []
    if stored_contract and stored_contract.get("contract_profile"):
        contract_query_docs = select_contract_query_docs(query, stored_contract)

    # Fetch docs from store for BM25 (filtered by document_id)
    store = ChromaStore()
    all_docs = store.get_all_documents(source=document_id)

    if document_id and not all_docs:
        raise HTTPException(
            status_code=404,
            detail=f"No indexed content found for document_id '{document_id}'."
        )

    docs = []

    if contract_query_docs:
        docs = [clause["clause_text"] for clause in contract_query_docs if clause.get("clause_text")]

    if not docs:
        vector = VectorRetriever()
        bm25 = BM25Retriever(all_docs)
        hybrid = HybridRetriever(vector, bm25)

        try:
            results = hybrid.retrieve(query, k=10, document_id=document_id)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve supporting context for the query."
            ) from exc

        if not results:
            raise HTTPException(
                status_code=404,
                detail="No relevant context found for the query."
            )

        reranker = Reranker()
        try:
            final_docs = reranker.rerank(query, results, top_k=5)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Failed to rerank retrieved context."
            ) from exc

        print(f"\n--- RETRIEVED CHUNKS FOR QUERY ---")
        for i, chunk in enumerate(final_docs):
            print(f"Chunk {i+1}: {chunk['content'][:200]}...\n")
        print(f"--- END CHUNKS ---\n")

        docs = [doc["content"] for doc in final_docs]

    generator = StructuredGenerator()
    ensure_generation_ready(generator)

    try:
        output = generator.generate(query=query, docs=docs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate a response for the query."
        ) from exc

    return output


@app.patch("/contracts/{document_id}/findings/{finding_index}/status")
def update_contract_finding_status(document_id: str, finding_index: int, payload: FindingStatusUpdate):
    allowed_statuses = {"open", "reviewed", "accepted", "dismissed", "escalated"}
    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid finding status.")

    store = InsightStore()
    updated_finding = store.update_review_finding_status(document_id, finding_index, payload.status)

    if not updated_finding:
        raise HTTPException(status_code=404, detail="Contract or finding not found.")

    return {
        "document_id": document_id,
        "finding_index": finding_index,
        "finding": updated_finding,
    }


@app.patch("/contracts/{document_id}/findings/{finding_index}/note")
def update_contract_finding_note(document_id: str, finding_index: int, payload: FindingNoteUpdate):
    store = InsightStore()
    updated_finding = store.update_review_finding_note(
        document_id,
        finding_index,
        payload.reviewer_note.strip(),
    )

    if not updated_finding:
        raise HTTPException(status_code=404, detail="Contract or finding not found.")

    return {
        "document_id": document_id,
        "finding_index": finding_index,
        "finding": updated_finding,
    }
