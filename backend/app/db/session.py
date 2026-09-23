"""
SQLAlchemy database session and engine setup for NagarSetu.
Supports PostgreSQL (production/docker) with flexible engine fallback for local testing.
"""

import os
import logging
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("nagarsetu.db")


def normalize_db_url(raw_url: str) -> str:
    """Normalize async, legacy, and cloud provider PostgreSQL URLs to standard synchronous psycopg2."""
    if not raw_url:
        return raw_url
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg2://" + url[len("postgresql+asyncpg://"):]
    elif url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


# Determine effective database URL
raw_db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
sync_db_url = normalize_db_url(raw_db_url)

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
    except Exception as exc:
        if use_sqlite_fallback == "false":
            logger.error("Failed to connect to PostgreSQL database and fallback is disabled: %s", exc)
            raise
        # Fallback to local dev SQLite so developers / deploys without PostgreSQL can run safely
        fallback_path = settings.DATA_PROCESSED_DIR.parent / "nagarsetu_dev.db"
        logger.warning(
            "PostgreSQL connection failed (%s). Gracefully falling back to local SQLite at %s",
            exc,
            fallback_path
        )
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
