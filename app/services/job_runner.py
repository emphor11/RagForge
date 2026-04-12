import os
import tempfile
from pathlib import Path

from app.services.job_store import job_store, utcnow
from app.services.supabase_storage import SupabaseStorage


def _get_pipeline():
    from app.api.main import ensure_generation_ready, get_pipeline

    pipeline = get_pipeline()
    ensure_generation_ready(pipeline.generator)
    return pipeline


def process_document_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        return

    source_path = job["source_path"]
    temp_path = None

    try:
        storage = SupabaseStorage()
        pipeline = _get_pipeline()

        if source_path.startswith("supabase://"):
            job_store.update_job(job_id, stage="downloading_source")
            remote_path = source_path.removeprefix("supabase://")
            file_bytes = storage.download_file(remote_path)
            suffix = Path(job["filename"]).suffix or ".bin"
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            handle.write(file_bytes)
            handle.flush()
            handle.close()
            temp_path = handle.name
        else:
            temp_path = source_path

        job_store.update_job(job_id, stage="analyzing_document")
        pipeline.run(temp_path, job["document_id"])
        job_store.update_job(
            job_id,
            status="completed",
            stage="completed",
            error=None,
            completed_at=utcnow(),
        )
    except ValueError as exc:
        print(f"❌ Job {job_id} validation error: {exc}")
        job_store.update_job(job_id, status="failed", stage="failed", error=str(exc))
    except Exception as exc:
        print(f"❌ Job {job_id} failed: {exc}")
        job_store.update_job(
            job_id,
            status="failed",
            stage="failed",
            error="Analysis failed during worker processing.",
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
