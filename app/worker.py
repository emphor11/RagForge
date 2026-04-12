import os
import time

from app.services.job_runner import process_document_job
from app.services.job_store import ensure_db_tables, job_store


POLL_INTERVAL = float(os.getenv("JOB_POLL_INTERVAL_SECONDS", "5"))


def run_worker():
    print("Starting document analysis worker...")
    ensure_db_tables()
    recovered = job_store.mark_failed_interrupted_jobs()
    if recovered:
        print(f"Recovered {recovered} interrupted jobs and marked them failed.")

    while True:
        job = job_store.claim_next_job()
        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        print(
            f"Worker claimed job {job['job_id']} for document {job['document_id']}."
        )
        process_document_job(job["job_id"])


if __name__ == "__main__":
    run_worker()
