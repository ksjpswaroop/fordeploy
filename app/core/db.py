import sqlite3
from typing import Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# SQLAlchemy connection
engine = create_engine(
    settings.SQLITE_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_sqlite_connection(db_path: str = "jobs.db") -> sqlite3.Connection:
    """Get direct SQLite connection for raw SQL operations"""
    return sqlite3.connect(db_path)
