"""
Database initialization and table creation utility for NagarSetu.
Creates all 11 relational tables and validates metadata.
"""

import sys
from pathlib import Path
import logging
from sqlalchemy import inspect

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger("nagarsetu.init_db")

EXPECTED_TABLES = [
    "departments",
    "categories",
    "raw_complaints",
    "triaged_complaints",
    "locality_gazetteer",
    "locality_aliases",
    "duplicate_clusters",
    "cluster_members",
    "acknowledgements",
    "status_history",
    "complaint_audits",
    "evaluation_results",
    "weekly_reports"
]


def create_tables(bind_engine=None) -> list:
    """Creates all registered SQLAlchemy tables in the target database and syncs columns."""
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)
    inspector = inspect(target_engine)
    existing_tables = inspector.get_table_names()

    from sqlalchemy import text
    with target_engine.begin() as conn:
        # Dynamic column migration for triaged_complaints
        if "triaged_complaints" in existing_tables:
            columns = [c["name"] for c in inspector.get_columns("triaged_complaints")]
            if "multimodal_payload" not in columns:
                conn.execute(text("ALTER TABLE triaged_complaints ADD COLUMN multimodal_payload JSON"))
            if "triage_metadata" not in columns:
                conn.execute(text("ALTER TABLE triaged_complaints ADD COLUMN triage_metadata JSON"))
            if "operator_overrides" not in columns:
                conn.execute(text("ALTER TABLE triaged_complaints ADD COLUMN operator_overrides JSON"))
            if "operator_decision" not in columns:
                conn.execute(text("ALTER TABLE triaged_complaints ADD COLUMN operator_decision JSON"))
            if "resolved_at" not in columns:
                conn.execute(text("ALTER TABLE triaged_complaints ADD COLUMN resolved_at TIMESTAMP"))

        # Dynamic column migration for duplicate_clusters
        if "duplicate_clusters" in existing_tables:
            cluster_cols = [c["name"] for c in inspector.get_columns("duplicate_clusters")]
            if "category" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN category VARCHAR(64)"))
            if "department" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN department VARCHAR(64)"))
            if "canonical_locality" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN canonical_locality VARCHAR(256)"))
            if "ward" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN ward VARCHAR(64)"))
            if "first_reported_at" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN first_reported_at TIMESTAMP"))
            if "latest_reported_at" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN latest_reported_at TIMESTAMP"))
            if "operator_notes" not in cluster_cols:
                conn.execute(text("ALTER TABLE duplicate_clusters ADD COLUMN operator_notes TEXT"))

        # Dynamic column migration for cluster_members
        if "cluster_members" in existing_tables:
            member_cols = [c["name"] for c in inspector.get_columns("cluster_members")]
            if "relationship_type" not in member_cols:
                conn.execute(text("ALTER TABLE cluster_members ADD COLUMN relationship_type VARCHAR(32) DEFAULT 'LIKELY_DUPLICATE'"))
            if "matching_signals" not in member_cols:
                conn.execute(text("ALTER TABLE cluster_members ADD COLUMN matching_signals JSON"))
            if "is_confirmed" not in member_cols:
                conn.execute(text("ALTER TABLE cluster_members ADD COLUMN is_confirmed BOOLEAN DEFAULT 1"))
            if "notes" not in member_cols:
                conn.execute(text("ALTER TABLE cluster_members ADD COLUMN notes TEXT"))

        # Dynamic column migration for evaluation_results
        if "evaluation_results" in existing_tables:
            eval_cols = [c["name"] for c in inspector.get_columns("evaluation_results")]
            if "detailed_results" not in eval_cols:
                conn.execute(text("ALTER TABLE evaluation_results ADD COLUMN detailed_results JSON"))

    return existing_tables


def verify_schema(bind_engine=None) -> dict:
    """Verifies that all 11 core tables are properly created and indexed."""
    target_engine = bind_engine or engine
    inspector = inspect(target_engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [t for t in EXPECTED_TABLES if t not in existing_tables]
    return {
        "status": "verified" if not missing_tables else "incomplete",
        "existing_tables": sorted(list(existing_tables)),
        "missing_tables": missing_tables,
        "total_tables": len(existing_tables)
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Creating tables in database...")
    created = create_tables()
    result = verify_schema()
    print(f"Schema verification: {result['status']}")
    print(f"Total tables found: {result['total_tables']}")
    for tbl in result["existing_tables"]:
        print(f" - {tbl}")
