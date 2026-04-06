import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings
from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.environ.get("POSTGRES_URL", "sqlite:///./ragforge_local.db")

# Detect test configuration vs production Postgres
is_sqlite = POSTGRES_URL.startswith("sqlite")

try:
    engine = create_engine(
        POSTGRES_URL, 
        connect_args={"check_same_thread": False} if is_sqlite else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

except Exception as e:
    print(f"Failed to connect to Database: {e}")
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
