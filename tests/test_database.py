"""
Database and Data Model Verification Tests for NagarSetu Phase 2.
Verifies all 11 relational concepts, table creation, alias resolution,
acknowledgement status transitions, and raw data immutability enforcement.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone

# Bootstrap backend directory
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import SessionLocal, engine
from app.db.init_db import create_tables, verify_schema
from app.models.taxonomy import Department, Category
from app.models.gazetteer import LocalityGazetteer, LocalityAlias
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory, ImmutableDataError
from app.models.cluster import DuplicateCluster, ClusterMember
from app.models.acknowledgement import Acknowledgement
from app.models.analytics import WeeklyReport, EvaluationResult


class TestDatabaseModels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_tables(bind_engine=engine)

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        try:
            self.db.rollback()
        except Exception:
            pass
        self.db.close()

    def test_01_all_tables_exist(self):
        """Verify that all 11 core tables and supporting index tables exist."""
        result = verify_schema(bind_engine=engine)
        self.assertEqual(result["status"], "verified")
        self.assertGreaterEqual(result["total_tables"], 11)

        expected = [
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
            "evaluation_results",
            "weekly_reports"
        ]
        for tbl in expected:
            self.assertIn(tbl, result["existing_tables"], f"Table '{tbl}' must exist in database")

    def test_02_department_and_category_taxonomy(self):
        """Verify 8 departments and category linkages."""
        departments = self.db.query(Department).all()
        dept_codes = {d.code for d in departments}
        self.assertGreaterEqual(len(departments), 8)
        for req_code in ["RDS", "WSS_WATER", "SWM", "WSS_SEWER", "ELEC", "HORT", "HLT", "GEN"]:
            self.assertIn(req_code, dept_codes)

        categories = self.db.query(Category).all()
        self.assertGreaterEqual(len(categories), 15)

        # Verify category relationships
        roads_cat = self.db.query(Category).filter(Category.category_id == "CAT_POTHOLE").first()
        self.assertIsNotNone(roads_cat)
        self.assertEqual(roads_cat.department.code, "RDS")
        self.assertIsInstance(roads_cat.subcategories, list)

    def test_03_gazetteer_alias_resolution(self):
        """Verify locality gazetteer and multiple alias resolution for MP Nagar."""
        mp_nagar = self.db.query(LocalityGazetteer).filter(
            LocalityGazetteer.canonical_locality == "MP Nagar"
        ).first()
        self.assertIsNotNone(mp_nagar)
        self.assertEqual(mp_nagar.ward, "Ward 42")
        self.assertEqual(mp_nagar.zone, "Central Zone")

        # Test alias queries
        test_aliases = ["mp nagar", "m.p. nagar", "mpnagar", "m p nagar", "maharana pratap nagar"]
        for alias_input in test_aliases:
            match = self.db.query(LocalityAlias).filter(
                LocalityAlias.alias_normalized == alias_input
            ).first()
            self.assertIsNotNone(match, f"Alias '{alias_input}' should resolve")
            self.assertEqual(match.canonical_locality, "MP Nagar")

    def test_04_raw_complaints_seeded_and_multilingual(self):
        """Verify at least 30 synthetic complaints across English, Hindi, and Hinglish."""
        complaints = self.db.query(RawComplaint).all()
        self.assertGreaterEqual(len(complaints), 30)

        # Check languages in triaged complaints
        triaged = self.db.query(TriagedComplaint).all()
        languages = {t.language for t in triaged}
        self.assertIn("en", languages)
        self.assertIn("hi", languages)

        # Check channels
        channels = {c.channel for c in complaints}
        self.assertIn("state_helpline", channels)
        self.assertIn("municipal_app", channels)
        self.assertIn("social_media", channels)
        self.assertIn("elected_rep_message", channels)

    def test_05_raw_data_immutability_enforcement(self):
        """
        CRITICAL ARCHITECTURAL TEST:
        Verify that RawComplaint records are STRICTLY IMMUTABLE.
        Updating or deleting a raw complaint MUST raise ImmutableDataError.
        """
        raw = self.db.query(RawComplaint).first()
        self.assertIsNotNone(raw)
        original_text = raw.text

        # 1. Attempt UPDATE -> Must raise ImmutableDataError
        raw.text = "Tampered text that should be blocked"
        with self.assertRaises(ImmutableDataError):
            self.db.commit()
        self.db.rollback()

        # Verify value was not altered
        refreshed = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == raw.complaint_id).first()
        self.assertEqual(refreshed.text, original_text)

        # 2. Attempt DELETE -> Must raise ImmutableDataError
        self.db.delete(refreshed)
        with self.assertRaises(ImmutableDataError):
            self.db.commit()
        self.db.rollback()

        # Verify record still exists
        survived = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == raw.complaint_id).first()
        self.assertIsNotNone(survived)

    def test_06_triaged_complaint_separation(self):
        """Verify triaged complaint is stored separately from raw complaint and can be updated."""
        triaged = self.db.query(TriagedComplaint).first()
        self.assertIsNotNone(triaged)
        self.assertIsNotNone(triaged.raw_complaint)
        self.assertNotEqual(triaged.raw_complaint.text, "")

        # Triaged complaints CAN be updated (e.g. by operator review)
        original_status = triaged.processing_status
        triaged.processing_status = "OPERATOR_APPROVED"
        self.db.commit()

        reloaded = self.db.query(TriagedComplaint).filter(TriagedComplaint.id == triaged.id).first()
        self.assertEqual(reloaded.processing_status, "OPERATOR_APPROVED")

        # Revert for cleanliness
        reloaded.processing_status = original_status
        self.db.commit()

    def test_07_duplicate_clusters_and_members(self):
        """Verify cluster grouping preserves individual raw complaint integrity."""
        cluster = self.db.query(DuplicateCluster).filter(
            DuplicateCluster.cluster_id == "CLUST-MPNAGAR-POTHOLE-01"
        ).first()
        if not cluster:
            cluster = self.db.query(DuplicateCluster).first()
        self.assertIsNotNone(cluster)
        self.assertGreaterEqual(len(cluster.members), 2)
        member_ids = [m.complaint_id for m in cluster.members]
        self.assertGreaterEqual(len(member_ids), 2)

        # Verify raw complaints remain separate
        raw_1 = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == member_ids[0]).first()
        raw_2 = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == member_ids[1]).first()
        self.assertIsNotNone(raw_1)
        self.assertIsNotNone(raw_2)
        self.assertNotEqual(raw_1.complaint_id, raw_2.complaint_id)

    def test_08_acknowledgement_status_and_no_dispatch(self):
        """
        Verify Acknowledgement model:
        - Status must be one of 'draft', 'edited', 'approved'
        - STRICTLY NO send or external delivery fields exist on the table.
        """
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("acknowledgements")]
        # Assert NO external delivery columns
        forbidden = ["is_sent", "sent_at", "delivered_at", "external_message_id", "dispatch_status", "recipient_phone"]
        for f in forbidden:
            self.assertNotIn(f, columns, f"Acknowledgement model must not have delivery field '{f}'")

        # Verify existing acknowledgements have allowed statuses
        acks = self.db.query(Acknowledgement).all()
        for ack in acks:
            self.assertIn(ack.status, ["draft", "edited", "approved"])

    def test_09_status_history_audit_trail(self):
        """Verify status history captures audit trail of state changes."""
        history = self.db.query(StatusHistory).filter(StatusHistory.complaint_id == "CMP-SYN-001").all()
        self.assertGreaterEqual(len(history), 2)
        new_statuses = [h.new_status for h in history]
        self.assertIn("RAW", new_statuses)

    def test_10_evaluation_and_weekly_reports(self):
        """Verify weekly reports and evaluation results tables."""
        evals = self.db.query(EvaluationResult).all()
        self.assertGreaterEqual(len(evals), 1)
        ev = evals[0]
        self.assertTrue(0.0 <= ev.department_accuracy <= 1.0)
        self.assertTrue(ev.is_synthetic_benchmark)

        reports = self.db.query(WeeklyReport).all()
        self.assertGreaterEqual(len(reports), 1)
        r = reports[0]
        self.assertGreater(r.complaints_received, 0)
        self.assertIsInstance(r.top_categories, list)


class TestDatabaseStartupAndIdempotency(unittest.TestCase):
    """
    Verification tests for production startup initialization:
    - Verifies URL normalization for Render PostgreSQL and legacy URLs.
    - Verifies idempotent initialization on a fresh database.
    - Verifies repeating initialization does not duplicate records or drop tables.
    - Verifies health check reports the active database engine and verified tables.
    - Verifies GET /api/v1/complaints succeeds against initialized database.
    """

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_init.db"
        self.test_engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)

    def tearDown(self):
        import shutil
        self.test_engine.dispose()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_url_normalization(self):
        """Verify URL normalization for Render (postgres://) and standard URLs."""
        from app.db.session import normalize_db_url
        self.assertEqual(
            normalize_db_url("postgres://user:pass@dpg-xxx.render.com/db"),
            "postgresql+psycopg2://user:pass@dpg-xxx.render.com/db"
        )
        self.assertEqual(
            normalize_db_url("postgresql://user:pass@dpg-xxx.render.com/db"),
            "postgresql+psycopg2://user:pass@dpg-xxx.render.com/db"
        )
        self.assertEqual(
            normalize_db_url("postgresql+asyncpg://user:pass@host/db"),
            "postgresql+psycopg2://user:pass@host/db"
        )
        self.assertEqual(
            normalize_db_url("sqlite:///data/test.db"),
            "sqlite:///data/test.db"
        )

    def test_fresh_database_initialization(self):
        """Verify a fresh empty database gets all tables and baseline seed data."""
        from app.db.init_db import init_database_and_seed
        res = init_database_and_seed(bind_engine=self.test_engine, session_factory=self.test_session_factory)
        self.assertEqual(res["status"], "verified")
        self.assertGreaterEqual(res["total_tables"], 11)

        with self.test_session_factory() as db:
            dept_count = db.query(Department).count()
            complaint_count = db.query(RawComplaint).count()
            gazetteer_count = db.query(LocalityGazetteer).count()
            self.assertGreaterEqual(dept_count, 8)
            self.assertGreaterEqual(complaint_count, 30)
            self.assertGreaterEqual(gazetteer_count, 10)

    def test_idempotent_reinitialization(self):
        """Verify running initialization twice does NOT duplicate data or drop tables."""
        from app.db.init_db import init_database_and_seed
        # First initialization
        init_database_and_seed(bind_engine=self.test_engine, session_factory=self.test_session_factory)
        with self.test_session_factory() as db:
            dept_count_1 = db.query(Department).count()
            complaint_count_1 = db.query(RawComplaint).count()
            gazetteer_count_1 = db.query(LocalityGazetteer).count()

        # Second initialization
        init_database_and_seed(bind_engine=self.test_engine, session_factory=self.test_session_factory)
        with self.test_session_factory() as db:
            dept_count_2 = db.query(Department).count()
            complaint_count_2 = db.query(RawComplaint).count()
            gazetteer_count_2 = db.query(LocalityGazetteer).count()

        self.assertEqual(dept_count_1, dept_count_2, "Department records must not be duplicated")
        self.assertEqual(complaint_count_1, complaint_count_2, "Complaint records must not be duplicated")
        self.assertEqual(gazetteer_count_1, gazetteer_count_2, "Gazetteer records must not be duplicated")

    def test_health_reports_engine_and_tables(self):
        """Verify /health endpoint returns active database engine and verified table count."""
        from app.main import health_check
        health = health_check()
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["checks"]["database"], "healthy")
        self.assertEqual(health["checks"]["database_tables"], "all_present")
        self.assertIn("database_engine", health["details"])
        self.assertIn(health["details"]["database_engine"], ("sqlite", "postgresql"))
        self.assertGreaterEqual(health["details"]["tables_verified"], 11)

    def test_complaints_endpoint_returns_data(self):
        """Verify GET /api/v1/complaints succeeds against initialized database with 200 OK."""
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        response = client.get("/api/v1/complaints")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("data", data)
        self.assertIn("pagination", data)
        self.assertGreater(data["pagination"]["total_records"], 0)


if __name__ == "__main__":
    unittest.main()

