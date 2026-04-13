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


def call_ollama(prompt: str) -> dict[str, Any]:
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
        local_stack = "ready"
        try:
            os.environ.setdefault("LOCAL_MODEL_FILES_ONLY", "false")
            from app.services.local_deep_verify import LocalHybridVerifier

            LocalHybridVerifier("__healthcheck__")
        except Exception as exc:
            local_stack = f"unavailable: {exc}"
        return {
            "status": "ok",
            "ollama_url": LOCAL_OLLAMA_URL,
            "model": LOCAL_OLLAMA_MODEL,
            "available_models": [item.get("name") for item in models],
            "local_parity_stack": local_stack,
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
        os.environ.setdefault("LOCAL_MODEL_FILES_ONLY", "false")
        from app.services.local_deep_verify import (
            LocalHybridVerifier,
            build_final_verification_payload,
            build_ollama_prompt,
        )

        parity_verifier = LocalHybridVerifier(payload.document_id)
        parity_result = parity_verifier.build_verification_result(source_document)
        ollama_prompt = build_ollama_prompt(
            source_document,
            parity_result,
            max_context_chars=OLLAMA_MAX_RAW_CHARS,
        )
        ollama_result = parse_ollama_response(call_ollama(ollama_prompt))
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                f"Local Ollama timed out after {OLLAMA_TIMEOUT_SECONDS} seconds. "
                "Try a smaller model or raise OLLAMA_TIMEOUT_SECONDS."
            ),
        ) from exc
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local Deep Verify parity dependencies are missing. "
                "Install them with `pip install -r requirements-local-verify.txt`."
            ),
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Local Ollama request failed: {exc.reason}",
        ) from exc
    verification_payload = build_final_verification_payload(
        source_document,
        parity_result,
        ollama_result,
        provider=LOCAL_OLLAMA_MODEL,
    )

    save_verification(backend_url, payload.document_id, verification_payload)
    return {
        "status": "completed",
        "document_id": payload.document_id,
        "verification_mode": verification_payload["verification_mode"],
        "provider": LOCAL_OLLAMA_MODEL,
        "summary": verification_payload["verification_summary"],
    }
