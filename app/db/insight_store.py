import json
import os
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.audit import DocumentMetadata, AuditLog
from datetime import datetime, timezone
from app.services.supabase_storage import SupabaseStorage

class InsightStore:
    def __init__(self, base_path="insights"):
        self.storage = SupabaseStorage()
        self.folder = "insights" # Folder inside our Supabase bucket

    def save(self, document_id: str, data: dict):
        import time
        if "uploaded_at" not in data:
            data["uploaded_at"] = time.time()

        # 1. Save to Supabase Storage (Cloud JSON)
        json_data = json.dumps(data, indent=2).encode('utf-8')
        remote_path = f"{self.folder}/{document_id}.json"
        self.storage.upload_bytes(json_data, remote_path)

        # 2. Sync to Postgres (Supabase/Neon)
        db = SessionLocal()
        try:
            meta = db.query(DocumentMetadata).filter(DocumentMetadata.document_id == document_id).first()
            if not meta:
                profile = data.get("contract_profile", {})
                meta = DocumentMetadata(
                    document_id=document_id,
                    document_type=profile.get("document_type", "unknown"),
                    status="reviewed",
                )
                db.add(meta)
            else:
                profile = data.get("contract_profile", {})
                if profile.get("document_type"):
                    meta.document_type = profile.get("document_type")
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ Database Sync Error: {e}")
        finally:
            db.close()

    def load(self, document_id: str):
        try:
            remote_path = f"{self.folder}/{document_id}.json"
            bytes_data = self.storage.download_file(remote_path)
            return json.loads(bytes_data)
        except Exception:
            return None

    def update_review_finding_status(self, document_id: str, finding_index: int, status: str, user_id: str = "anonymous"):
        data = self.load(document_id)
        if not data: return None
        findings = data.get("review_findings", [])
        if finding_index < 0 or finding_index >= len(findings): return None

        finding = findings[finding_index]
        finding["status"] = status
        self.save(document_id, data)

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
        finally:
            db.close()
        return finding

    def list_all(self):
        docs = []
        try:
            files = self.storage.list_files(self.folder)
            for f in files:
                if f['name'].endswith(".json"):
                    doc_id = f['name'].replace(".json", "")
                    # We use the 'created_at' from Supabase metadata
                    upload_date = f.get('created_at', "")
                    docs.append({
                        "id": doc_id, 
                        "filename": doc_id, 
                        "upload_date": upload_date
                    })
        except Exception as e:
            print(f"❌ Error listing files: {e}")
        return docs
