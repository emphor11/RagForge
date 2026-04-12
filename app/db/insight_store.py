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
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, document_id: str, data: dict):
        import time
        if "uploaded_at" not in data:
            data["uploaded_at"] = time.time()

        # 1. Save to Supabase Storage (Cloud JSON)
        if self.storage.is_configured():
            try:
                json_data = json.dumps(data, indent=2).encode('utf-8')
                remote_path = f"{self.folder}/{document_id}.json"
                self.storage.upload_bytes(json_data, remote_path)
            except Exception as e:
                print(f"❌ Supabase Storage Error: {e}")
        else:
            local_path = os.path.join(self.base_path, f"{document_id}.json")
            with open(local_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)

        # 2. Sync to Postgres (Supabase/Neon)
        if not SessionLocal:
            print("⚠️ Skipping database sync (Postgres not configured)")
            return

        db = SessionLocal()
        try:
            from app.models.audit import DocumentMetadata
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
        if self.storage.is_configured():
            try:
                remote_path = f"{self.folder}/{document_id}.json"
                bytes_data = self.storage.download_file(remote_path)
                return json.loads(bytes_data)
            except Exception:
                return None

        local_path = os.path.join(self.base_path, f"{document_id}.json")
        if not os.path.exists(local_path):
            return None

        with open(local_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def update_review_finding_status(self, document_id: str, finding_index: int, status: str, user_id: str = "anonymous"):
        data = self.load(document_id)
        if not data: return None
        findings = data.get("review_findings", [])
        if finding_index < 0 or finding_index >= len(findings): return None

        finding = findings[finding_index]
        finding["status"] = status
        self.save(document_id, data)

        if SessionLocal:
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
        else:
            print("⚠️ Skipping audit log (Postgres not configured)")
        return finding

    def update_review_finding_note(self, document_id: str, finding_index: int, reviewer_note: str, user_id: str = "anonymous"):
        data = self.load(document_id)
        if not data:
            return None

        findings = data.get("review_findings", [])
        if finding_index < 0 or finding_index >= len(findings):
            return None

        finding = findings[finding_index]
        finding["reviewer_note"] = reviewer_note
        self.save(document_id, data)

        if SessionLocal:
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
            except Exception:
                db.rollback()
            finally:
                db.close()

        return finding

    def delete(self, document_id: str):
        remote_path = f"{self.folder}/{document_id}.json"

        if self.storage.is_configured():
            try:
                self.storage.supabase.storage.from_(self.storage.bucket_name).remove([remote_path])
            except Exception as e:
                print(f"❌ Failed to delete {document_id} from storage: {e}")
        else:
            local_path = os.path.join(self.base_path, f"{document_id}.json")
            if os.path.exists(local_path):
                os.remove(local_path)

        if SessionLocal:
            db = SessionLocal()
            try:
                db.query(AuditLog).filter(AuditLog.document_id == document_id).delete()
                db.query(DocumentMetadata).filter(DocumentMetadata.document_id == document_id).delete()
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"❌ Failed to delete {document_id} from database: {e}")
            finally:
                db.close()

    def list_all(self):
        docs = []
        if self.storage.is_configured():
            try:
                files = self.storage.list_files(self.folder)
                for f in files:
                    if f['name'].endswith(".json"):
                        doc_id = f['name'].replace(".json", "")
                        upload_date = self._normalize_upload_date(f.get("created_at"))
                        docs.append({
                            "id": doc_id, 
                            "filename": doc_id, 
                            "upload_date": upload_date,
                            "status": "completed",
                        })
            except Exception as e:
                print(f"❌ Error listing files: {e}")
            return docs

        for name in os.listdir(self.base_path):
            if not name.endswith(".json"):
                continue
            local_path = os.path.join(self.base_path, name)
            docs.append(
                {
                    "id": name.replace(".json", ""),
                    "filename": name.replace(".json", ""),
                    "upload_date": os.path.getmtime(local_path),
                    "status": "completed",
                }
            )
        return docs

    def _normalize_upload_date(self, raw_value):
        if isinstance(raw_value, (int, float)):
            return float(raw_value)

        if isinstance(raw_value, str) and raw_value:
            try:
                return datetime.fromisoformat(
                    raw_value.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                pass

        return datetime.now(timezone.utc).timestamp()
