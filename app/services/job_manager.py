import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


class JobManager:
    def __init__(self, base_dir: str = "uploads/job_state", max_workers: int = 1):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}
        self._doc_to_job: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._load_jobs()

    def _job_path(self, job_id: str) -> Path:
        return self.base_dir / f"{job_id}.json"

    def _load_jobs(self):
        for path in self.base_dir.glob("*.json"):
            try:
                job = json.loads(path.read_text())
            except Exception:
                continue

            if job.get("status") in {"queued", "processing"}:
                job["status"] = "failed"
                job["error"] = "Job interrupted before completion. Please retry."
                job["updated_at"] = time.time()
                path.write_text(json.dumps(job, indent=2))

            job_id = job.get("job_id")
            document_id = job.get("document_id")
            if not job_id or not document_id:
                continue

            self._jobs[job_id] = job
            self._doc_to_job[document_id] = job_id

    def _persist_job(self, job: dict):
        self._job_path(job["job_id"]).write_text(json.dumps(job, indent=2))

    def _update_job(self, job_id: str, **changes):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            job.update(changes)
            job["updated_at"] = time.time()
            self._persist_job(job)
            return deepcopy(job)

    def create_job(self, document_id: str, filename: str, local_path: str):
        now = time.time()
        job_id = uuid.uuid4().hex
        job = {
            "job_id": job_id,
            "document_id": document_id,
            "filename": filename,
            "local_path": local_path,
            "status": "queued",
            "stage": "queued",
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._doc_to_job[document_id] = job_id
            self._persist_job(job)
        return deepcopy(job)

    def submit_job(self, job_id: str, func):
        self._executor.submit(func, job_id)

    def mark_processing(self, job_id: str, stage: str = "processing"):
        return self._update_job(job_id, status="processing", stage=stage, error=None)

    def mark_completed(self, job_id: str):
        return self._update_job(job_id, status="completed", stage="completed", error=None)

    def mark_failed(self, job_id: str, error: str):
        return self._update_job(job_id, status="failed", stage="failed", error=error)

    def update_stage(self, job_id: str, stage: str):
        return self._update_job(job_id, stage=stage)

    def get_job(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            return deepcopy(job) if job else None

    def get_job_by_document(self, document_id: str):
        with self._lock:
            job_id = self._doc_to_job.get(document_id)
            if not job_id:
                return None
            job = self._jobs.get(job_id)
            return deepcopy(job) if job else None

    def list_active_documents(self):
        with self._lock:
            active_jobs = []
            for job in self._jobs.values():
                if job.get("status") not in {"queued", "processing", "failed"}:
                    continue
                active_jobs.append(
                    {
                        "id": job["document_id"],
                        "filename": job["filename"],
                        "upload_date": job["created_at"],
                        "status": job["status"],
                        "stage": job.get("stage"),
                        "job_id": job["job_id"],
                        "error": job.get("error"),
                    }
                )
            return sorted(active_jobs, key=lambda item: item["upload_date"], reverse=True)


job_manager = JobManager()
