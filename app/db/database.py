import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Prioritize DATABASE_URL (Supabase) or POSTGRES_URL (Neon)
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "sqlite:///./ragforge_local.db"

# Supabase/Neon usually require SSL. 
# This handles the 'sslmode' if it's missing from the connection string.
if "sqlite" not in DATABASE_URL and "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

is_sqlite = DATABASE_URL.startswith("sqlite")

try:
    engine = create_engine(
        DATABASE_URL, 
        # check_same_thread is only needed for SQLite
        connect_args={"check_same_thread": False} if is_sqlite else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

except Exception as e:
    print(f"❌ Failed to connect to Database: {e}")
    SessionLocal = None
    Base = declarative_base()


def get_db():
    if not SessionLocal:
        yield None
        return
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
