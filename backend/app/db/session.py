"""
SQLAlchemy database session and engine setup for NagarSetu.
Supports PostgreSQL (production/docker) with flexible engine fallback for local testing.
"""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Determine effective database URL
raw_db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)

# Normalize async driver to sync driver for standard session operations if needed
sync_db_url = raw_db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
if sync_db_url.startswith("postgresql://"):
    sync_db_url = sync_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Check if SQLite fallback should be used for development/offline mode
use_sqlite_fallback = os.getenv("USE_SQLITE_FALLBACK", "auto").lower()

if use_sqlite_fallback == "true" or (use_sqlite_fallback == "auto" and "sqlite" in sync_db_url):
    # Ensure data directory exists for SQLite
    db_file_dir = settings.DATA_PROCESSED_DIR.parent
    db_file_dir.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}
    engine = create_engine(sync_db_url, connect_args=connect_args, echo=False)
else:
    # Attempt connecting to PostgreSQL; if unreachable in auto mode, graceful fallback to local SQLite
    try:
        connect_args = {}
        engine = create_engine(
            sync_db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args,
            echo=False
        )
        # Test connection
        if use_sqlite_fallback == "auto":
            with engine.connect() as conn:
                pass
    except Exception:
        # Fallback to local dev SQLite so developers can work offline without a running PostgreSQL daemon
        fallback_path = settings.DATA_PROCESSED_DIR.parent / "nagarsetu_dev.db"
        sync_db_url = f"sqlite:///{fallback_path}"
        engine = create_engine(sync_db_url, connect_args={"check_same_thread": False}, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing request-scoped database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
