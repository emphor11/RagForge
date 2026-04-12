from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base


class AuditLog(Base):
    """
    Immutable ledger of decisions made by attorneys on specific risk findings.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(255), index=True, nullable=False)
    finding_title = Column(Text, nullable=False)
    finding_type = Column(String(100), nullable=False)  # e.g. missing_protection

    # Action taken
    status = Column(String(50), nullable=False)  # 'accepted', 'dismissed', 'negotiate'
    user_id = Column(String(100), nullable=True)  # E.g., 'attorney_4'
    justification = Column(Text, nullable=True)

    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DocumentMetadata(Base):
    """
    Tracks overall document-level settings.
    """

    __tablename__ = "document_metadata"

    document_id = Column(String(255), primary_key=True, index=True)
    document_type = Column(String(100))
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default="reviewed")


class JobRecord(Base):
    """
    Durable job state for asynchronous document analysis.
    """

    __tablename__ = "job_records"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, index=True, nullable=False)
    document_id = Column(String(255), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    source_path = Column(Text, nullable=False)
    status = Column(String(50), index=True, nullable=False, default="queued")
    stage = Column(String(100), nullable=False, default="queued")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
