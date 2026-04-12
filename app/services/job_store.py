import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Optional

from app.db.database import Base, SessionLocal, engine
from app.models.audit import JobRecord


def utcnow():
    return datetime.now(timezone.utc)


def ensure_db_tables():
    if engine is None:
        return

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"❌ Failed to ensure database tables: {exc}")


def serialize_job(record: Optional[JobRecord]):
    if record is None:
        return None

    return {
        "job_id": record.job_id,
        "document_id": record.document_id,
        "filename": record.filename,
        "source_path": record.source_path,
        "status": record.status,
        "stage": record.stage,
        "error": record.error,
        "created_at": record.created_at.timestamp() if record.created_at else time.time(),
        "updated_at": record.updated_at.timestamp() if record.updated_at else time.time(),
        "started_at": record.started_at.timestamp() if record.started_at else None,
        "completed_at": record.completed_at.timestamp() if record.completed_at else None,
    }


class JobStore:
    def __init__(self):
        pass

    def create_job(self, document_id: str, filename: str, source_path: str):
        if not SessionLocal:
            raise RuntimeError("Database is not configured; jobs require persistent storage.")

        now = utcnow()
        record = JobRecord(
            job_id=uuid.uuid4().hex,
            document_id=document_id,
            filename=filename,
            source_path=source_path,
            status="queued",
            stage="queued",
            created_at=now,
            updated_at=now,
        )

        db = SessionLocal()
        try:
            db.add(record)
            db.commit()
            db.refresh(record)
            return serialize_job(record)
        finally:
            db.close()

    def list_pending_documents(self):
        if not SessionLocal:
            return []

        db = SessionLocal()
        try:
            records = (
                db.query(JobRecord)
                .filter(JobRecord.status.in_(["queued", "processing", "failed"]))
                .order_by(JobRecord.created_at.desc())
                .all()
            )
            return [
                {
                    "id": record.document_id,
                    "filename": record.filename,
                    "upload_date": record.created_at.timestamp() if record.created_at else time.time(),
                    "status": record.status,
                    "stage": record.stage,
                    "job_id": record.job_id,
                    "error": record.error,
                }
                for record in records
            ]
        finally:
            db.close()

    def get_job(self, job_id: str):
        if not SessionLocal:
            return None

        db = SessionLocal()
        try:
            record = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
            return serialize_job(record)
        finally:
            db.close()

    def get_job_by_document(self, document_id: str):
        if not SessionLocal:
            return None

        db = SessionLocal()
        try:
            record = (
                db.query(JobRecord)
                .filter(JobRecord.document_id == document_id)
                .order_by(JobRecord.created_at.desc())
                .first()
            )
            return serialize_job(record)
        finally:
            db.close()

    def claim_next_job(self):
        if not SessionLocal:
            return None

        db = SessionLocal()
        try:
            record = (
                db.query(JobRecord)
                .filter(JobRecord.status == "queued")
                .order_by(JobRecord.created_at.asc())
                .first()
            )
            if not record:
                return None

            now = utcnow()
            record.status = "processing"
            record.stage = "worker_claimed"
            record.started_at = now
            record.updated_at = now
            db.commit()
            db.refresh(record)
            return serialize_job(record)
        finally:
            db.close()

    def update_job(self, job_id: str, **changes):
        if not SessionLocal:
            return None

        db = SessionLocal()
        try:
            record = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()
            if not record:
                return None

            for key, value in changes.items():
                setattr(record, key, value)

            record.updated_at = utcnow()
            db.commit()
            db.refresh(record)
            return serialize_job(record)
        finally:
            db.close()

    def mark_failed_interrupted_jobs(self):
        if not SessionLocal:
            return 0

        db = SessionLocal()
        try:
            records = db.query(JobRecord).filter(JobRecord.status == "processing").all()
            count = 0
            for record in records:
                record.status = "failed"
                record.stage = "failed"
                record.error = "Worker interrupted before completion. Please retry."
                record.updated_at = utcnow()
                count += 1
            db.commit()
            return count
        finally:
            db.close()

    def delete_document_jobs(self, document_id: str):
        if not SessionLocal:
            return

        db = SessionLocal()
        try:
            db.query(JobRecord).filter(JobRecord.document_id == document_id).delete()
            db.commit()
        finally:
            db.close()


job_store = JobStore()
