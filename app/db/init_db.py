from app.db.database import engine, Base
from app.models.audit import AuditLog, DocumentMetadata
import os

def init_db():
    if not engine:
        print("No engine configured, skipping DB init.")
        return
        
    print(f"Creating tables in database...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Success! Tables created.")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    init_db()
