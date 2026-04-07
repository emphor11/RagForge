import json
import os
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.audit import DocumentMetadata, AuditLog
from datetime import datetime, timezone


class InsightStore:
    def __init__(self, base_path="insights"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, document_id: str, data: dict):
        import time

        if "uploaded_at" not in data:
            data["uploaded_at"] = time.time()

        # 1. Save to JSON (Legacy/Backup)
        path = os.path.join(self.base_path, f"{document_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # 2. Sync to Postgres (Neon)
        db = SessionLocal()
        try:
            # Check if metadata exists
            meta = (
                db.query(DocumentMetadata)
                .filter(DocumentMetadata.document_id == document_id)
                .first()
            )
            if not meta:
                profile = data.get("contract_profile", {})
                meta = DocumentMetadata(
                    document_id=document_id,
                    document_type=profile.get("document_type", "unknown"),
                    status="reviewed",
                )
                db.add(meta)
            else:
                # Update existing metadata if needed
                profile = data.get("contract_profile", {})
                if profile.get("document_type"):
                    meta.document_type = profile.get("document_type")

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Postgres Sync Error (save): {e}")
        finally:
            db.close()

    def load(self, document_id: str):
        path = os.path.join(self.base_path, f"{document_id}.json")

        if not os.path.exists(path):
            return None

        with open(path, "r") as f:
            json_data = json.load(f)

        return json_data

    def update_review_finding_status(
        self,
        document_id: str,
        finding_index: int,
        status: str,
        user_id: str = "anonymous",
    ):
        data = self.load(document_id)
        if not data:
            return None

        findings = data.get("review_findings", [])
        if finding_index < 0 or finding_index >= len(findings):
            return None

        finding = findings[finding_index]
        finding["status"] = status
        self.save(document_id, data)

        # Log to Audit Table
        db = SessionLocal()
        try:
            log = AuditLog(
                document_id=document_id,
                finding_title=finding.get("title", "Untitled"),
                finding_type=finding.get("finding_type", "risk"),
                status=status,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Postgres Audit Error (status): {e}")
        finally:
            db.close()

        return finding

    def update_review_finding_note(
        self,
        document_id: str,
        finding_index: int,
        reviewer_note: str,
        user_id: str = "anonymous",
    ):
        data = self.load(document_id)
        if not data:
            return None

        findings = data.get("review_findings", [])
        if finding_index < 0 or finding_index >= len(findings):
            return None

        finding = findings[finding_index]
        finding["reviewer_note"] = reviewer_note
        self.save(document_id, data)

        # Log to Audit Table (Status remains the same, but note is added)
        db = SessionLocal()
        try:
            log = AuditLog(
                document_id=document_id,
                finding_title=finding.get("title", "Untitled"),
                finding_type=finding.get("finding_type", "risk"),
                status=finding.get("status", "open"),
                user_id=user_id,
                justification=reviewer_note,
                timestamp=datetime.now(timezone.utc),
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Postgres Audit Error (note): {e}")
        finally:
            db.close()

        return finding

    def delete(self, document_id: str):
        # 1. Remove JSON File
        path = os.path.join(self.base_path, f"{document_id}.json")
        if os.path.exists(path):
            os.remove(path)

        # 2. Remove Postgres Metadata
        db = SessionLocal()
        try:
            db.query(DocumentMetadata).filter(
                DocumentMetadata.document_id == document_id
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Postgres Delete Error: {e}")
        finally:
            db.close()

    def list_all(self):
        docs = []

        if not os.path.exists(self.base_path):
            return []

        for filename in os.listdir(self.base_path):
            if filename.endswith(".json"):
                path = os.path.join(self.base_path, filename)
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        mtime = data.get("uploaded_at", os.path.getmtime(path))
                except Exception:
                    mtime = os.path.getmtime(path)
                doc_id = filename.replace(".json", "")

                docs.append({"id": doc_id, "filename": doc_id, "upload_date": mtime})

        # Sort by mtime (newest first)
        docs.sort(key=lambda x: x["upload_date"], reverse=True)

        return docs
