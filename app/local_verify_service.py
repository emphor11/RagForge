import json
import os
import ssl
from typing import Any
from urllib import error, parse, request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import certifi


LOCAL_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
LOCAL_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "420"))
OLLAMA_MAX_RAW_CHARS = int(os.getenv("OLLAMA_MAX_RAW_CHARS", "14000"))
VERIFY_BACKEND_SSL = os.getenv("VERIFY_BACKEND_SSL", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class VerifyRequest(BaseModel):
    backend_url: str
    document_id: str


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, method=method, data=data, headers=headers)
    context = None
    if url.startswith("https://"):
        if VERIFY_BACKEND_SSL:
            context = ssl.create_default_context(cafile=certifi.where())
        else:
            context = ssl._create_unverified_context()

    with request.urlopen(req, timeout=OLLAMA_TIMEOUT_SECONDS, context=context) as response:
        body = response.read()
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def fetch_document(backend_url: str, document_id: str) -> dict[str, Any]:
    encoded = parse.quote(document_id, safe="")
    return _http_json("GET", f"{backend_url}/insights/{encoded}")


def save_verification(backend_url: str, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = parse.quote(document_id, safe="")
    return _http_json("POST", f"{backend_url}/documents/{encoded}/verify-results", payload)


def call_ollama(document_payload: dict[str, Any]) -> dict[str, Any]:
    review_findings = document_payload.get("review_findings", [])
    raw_text = document_payload.get("raw_text", "")
    contract_profile = document_payload.get("contract_profile", {})

    compact_findings = [
        {
            "title": finding.get("title"),
            "finding_type": finding.get("finding_type"),
            "clause_type": finding.get("clause_type"),
            "severity": finding.get("severity"),
            "explanation": finding.get("explanation"),
            "source_quotes": finding.get("source_quotes", [])[:2],
        }
        for finding in review_findings[:12]
    ]

    prompt = f"""
You are performing a deep verification pass for a legal contract review.
Review the contract profile, the extracted review findings, and the raw source text.
Return ONLY valid JSON with this exact shape:
{{
  "verification_summary": "short summary",
  "evaluation": {{
    "score": 0,
    "status": "pass or fail or deferred",
    "recommendation": "short recommendation",
    "issues": ["..."]
  }},
  "review_audit": {{
    "score": 0,
    "status": "pass or fail or deferred",
    "recommendation": "short recommendation",
    "grounding_score": 0.0,
    "structure_score": 0.0,
    "coverage_score": 0.0,
    "issues": ["..."]
  }},
  "review_findings": [
    {{
      "title": "same title",
      "confidence": 0.0,
      "verification_note": "short note"
    }}
  ]
}}

Rules:
- Keep all scores between 0 and 100 except grounding_score/structure_score/coverage_score which must be between 0.0 and 1.0.
- review_findings should include one object for each finding in the input, matched by title.
- Lower confidence if a finding is weakly supported by the raw text.
- If support is strong, confidence can be high.
- Do not include markdown or explanation outside JSON.

Contract profile:
{json.dumps(contract_profile, ensure_ascii=True)}

Review findings:
{json.dumps(compact_findings, ensure_ascii=True)}

Raw contract text:
{raw_text[:OLLAMA_MAX_RAW_CHARS]}
"""

    return _http_json(
        "POST",
        f"{LOCAL_OLLAMA_URL}/api/generate",
        {
            "model": LOCAL_OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
    )


def parse_ollama_response(response: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = response.get("response", "")
        return json.loads(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Local Ollama returned an invalid verification payload.",
        ) from exc


def merge_verified_findings(
    original_findings: list[dict[str, Any]], verified_findings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    indexed = {
        item.get("title", "").strip(): item
        for item in verified_findings
        if item.get("title")
    }

    merged = []
    for finding in original_findings:
        patch = indexed.get(finding.get("title", "").strip(), {})
        updated = dict(finding)
        if "confidence" in patch:
            updated["confidence"] = patch["confidence"]
        if patch.get("verification_note"):
            updated["verification_note"] = patch["verification_note"]
        merged.append(updated)
    return merged


app = FastAPI(title="RAGForge Local Verify")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    try:
        tags = _http_json("GET", f"{LOCAL_OLLAMA_URL}/api/tags")
        models = tags.get("models", []) if isinstance(tags, dict) else []
        return {
            "status": "ok",
            "ollama_url": LOCAL_OLLAMA_URL,
            "model": LOCAL_OLLAMA_MODEL,
            "available_models": [item.get("name") for item in models],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Local Ollama is not reachable at {LOCAL_OLLAMA_URL}.",
        ) from exc


@app.post("/verify")
def verify_document(payload: VerifyRequest):
    backend_url = payload.backend_url.rstrip("/")
    try:
        source_document = fetch_document(backend_url, payload.document_id)
    except error.HTTPError as exc:
        raise HTTPException(
            status_code=exc.code,
            detail=f"Failed to fetch hosted document from {backend_url}.",
        ) from exc

    try:
        ollama_result = parse_ollama_response(call_ollama(source_document))
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                f"Local Ollama timed out after {OLLAMA_TIMEOUT_SECONDS} seconds. "
                "Try a smaller model or raise OLLAMA_TIMEOUT_SECONDS."
            ),
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Local Ollama request failed: {exc.reason}",
        ) from exc
    original_findings = source_document.get("review_findings", [])
    merged_findings = merge_verified_findings(
        original_findings,
        ollama_result.get("review_findings", []),
    )

    verification_payload = {
        "verification_mode": "local_ollama",
        "verification_provider": LOCAL_OLLAMA_MODEL,
        "verification_summary": ollama_result.get(
            "verification_summary",
            "Deep verification completed with local Ollama.",
        ),
        "evaluation": ollama_result.get(
            "evaluation",
            {
                "score": 0,
                "status": "deferred",
                "recommendation": "Local verification did not return an evaluation.",
                "issues": [],
            },
        ),
        "review_audit": ollama_result.get(
            "review_audit",
            {
                "score": 0,
                "status": "deferred",
                "recommendation": "Local verification did not return a review audit.",
                "grounding_score": 0.0,
                "structure_score": 0.0,
                "coverage_score": 0.0,
                "issues": [],
            },
        ),
        "review_findings": merged_findings,
    }

    save_verification(backend_url, payload.document_id, verification_payload)
    return {
        "status": "completed",
        "document_id": payload.document_id,
        "verification_mode": "local_ollama",
        "provider": LOCAL_OLLAMA_MODEL,
        "summary": verification_payload["verification_summary"],
    }
