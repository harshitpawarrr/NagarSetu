"""
Comprehensive Unit Test Suite for NagarSetu Phase 6:
Weekly Departmental Digest, Cluster Analytics, Emerging Alerts, and Held-Out Test Set Evaluation.

Verifies all 20 required test scenarios:
1. weekly received count
2. weekly resolved count
3. weekly pending count
4. median resolution calculation (and null handling when no resolved timestamps)
5. repeat locality aggregation
6. cluster ranking
7. emerging alert baseline calculation
8. emerging alert threshold
9. no false alert below threshold
10. held-out test import
11. department accuracy
12. category accuracy
13. urgency accuracy/agreement
14. locality accuracy
15. duplicate reduction
16. confusion matrix generation
17. no fabricated metrics
18. synthetic-data labeling
19. report API
20. evaluation API
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure backend directory is in sys.path
TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.init_db import create_tables
from app.models.taxonomy import Department, Category
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.models.cluster import DuplicateCluster, ClusterMember
from app.models.analytics import EvaluationResult
from app.services.analytics.weekly_digest_service import WeeklyDigestService
from app.services.analytics.repeat_locality_service import RepeatLocalityService
from app.services.analytics.emerging_alerts_service import EmergingAlertsService
from app.services.evaluation.evaluation_service import EvaluationService
from app.schemas.evaluation import EvaluationRunRequest
from app.main import app
from app.db.session import get_db


class TestAnalyticsAndEvaluation(unittest.TestCase):
    """
    Unit test suite validating Phase 6 weekly digests, repeat analytics,
    emerging issue early warning alerts, and held-out benchmark evaluation.
    """

    @classmethod
    def setUpClass(cls):
        # In-memory SQLite with StaticPool
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        create_tables(bind_engine=cls.engine)

        # Seed standard municipal departments
        with cls.SessionLocal() as session:
            session.add_all([
                Department(department_id="DEPT_RDS", name="Roads & Footpaths", code="RDS", default_sla_hours=72),
                Department(department_id="DEPT_WSS", name="Water Supply & Sewerage", code="WSS", default_sla_hours=48),
                Department(department_id="DEPT_ELEC", name="Street Lighting & Elec", code="ELEC", default_sla_hours=48),
                Department(department_id="DEPT_SWM", name="Solid Waste Management", code="SWM", default_sla_hours=24),
                Category(category_id="CAT_ROAD_MAINTENANCE", department_id="DEPT_RDS", name="Potholes & Roads"),
                Category(category_id="CAT_WATER_SUPPLY", department_id="DEPT_WSS", name="Water Supply"),
                Category(category_id="CAT_STREET_LIGHTING", department_id="DEPT_ELEC", name="Streetlights"),
                Category(category_id="CAT_GARBAGE_COLLECTION", department_id="DEPT_SWM", name="Garbage Dumps"),
            ])
            session.commit()

        cls.weekly_digest_service = WeeklyDigestService()
        cls.repeat_locality_service = RepeatLocalityService()
        cls.emerging_alerts_service = EmergingAlertsService()
        cls.evaluation_service = EvaluationService()

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def setUp(self):
        # Clean complaints and clusters between tests
        with self.SessionLocal() as session:
            session.query(ClusterMember).delete()
            session.query(DuplicateCluster).delete()
            session.query(TriagedComplaint).delete()
            session.query(RawComplaint).delete()
            session.query(EvaluationResult).delete()
            session.commit()

    # 1. weekly received count
    def test_01_weekly_received_count(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # 2 complaints within last 3 days
            for i in range(2):
                raw = RawComplaint(
                    complaint_id=f"REC_IN_{i}",
                    channel="CITIZEN_APP",
                    text=f"Road damage {i}",
                    created_at=now - timedelta(days=2)
                )
                session.add(raw)
                t = TriagedComplaint(
                    complaint_id=f"REC_IN_{i}",
                    department="DEPT_RDS",
                    category="CAT_ROAD_MAINTENANCE",
                    urgency="MEDIUM",
                    processing_status="TRIAGED",
                    processed_at=now - timedelta(days=2)
                )
                session.add(t)

            # 1 complaint older than 10 days
            raw_old = RawComplaint(
                complaint_id="REC_OLD",
                channel="CITIZEN_APP",
                text="Old complaint",
                created_at=now - timedelta(days=12)
            )
            session.add(raw_old)
            t_old = TriagedComplaint(
                complaint_id="REC_OLD",
                department="DEPT_RDS",
                category="CAT_ROAD_MAINTENANCE",
                urgency="LOW",
                processing_status="TRIAGED",
                processed_at=now - timedelta(days=12)
            )
            session.add(t_old)
            session.commit()

            digest = self.weekly_digest_service.generate_weekly_digest(session, days_back=7)
            self.assertEqual(digest.overall_received, 2)
            dept_rds = next(d for d in digest.departments if d.department == "DEPT_RDS")
            self.assertEqual(dept_rds.complaints_received, 2)

    # 2. weekly resolved count
    def test_02_weekly_resolved_count(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # 1 resolved within window
            raw = RawComplaint(
                complaint_id="RES_1",
                channel="HELPLINE",
                text="Fixed leak",
                created_at=now - timedelta(days=4)
            )
            session.add(raw)
            t = TriagedComplaint(
                complaint_id="RES_1",
                department="DEPT_WSS",
                category="CAT_WATER_SUPPLY",
                urgency="HIGH",
                processing_status="RESOLVED",
                resolved_at=now - timedelta(days=1)
            )
            session.add(t)

            # 1 still open
            raw2 = RawComplaint(
                complaint_id="RES_2",
                channel="HELPLINE",
                text="Still leaking",
                created_at=now - timedelta(days=3)
            )
            session.add(raw2)
            t2 = TriagedComplaint(
                complaint_id="RES_2",
                department="DEPT_WSS",
                category="CAT_WATER_SUPPLY",
                urgency="HIGH",
                processing_status="OPERATOR_APPROVED"
            )
            session.add(t2)
            session.commit()

            digest = self.weekly_digest_service.generate_weekly_digest(session, days_back=7)
            self.assertEqual(digest.overall_resolved, 1)
            dept_wss = next(d for d in digest.departments if d.department == "DEPT_WSS")
            self.assertEqual(dept_wss.complaints_resolved, 1)

    # 3. weekly pending count
    def test_03_weekly_pending_count(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            raw = RawComplaint(
                complaint_id="PEND_1",
                channel="SOCIAL_MEDIA",
                text="Pothole",
                created_at=now - timedelta(days=1)
            )
            session.add(raw)
            t = TriagedComplaint(
                complaint_id="PEND_1",
                department="DEPT_RDS",
                processing_status="OPERATOR_REVIEW_PENDING"
            )
            session.add(t)
            session.commit()

            digest = self.weekly_digest_service.generate_weekly_digest(session, days_back=7)
            self.assertEqual(digest.overall_pending, 1)
            dept_rds = next(d for d in digest.departments if d.department == "DEPT_RDS")
            self.assertEqual(dept_rds.complaints_pending, 1)

    # 4. median resolution calculation (and null handling when no resolved timestamps)
    def test_04_median_resolution_calculation_and_null_handling(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # First verify null handling: resolved with no resolved_at
            raw_null = RawComplaint(
                complaint_id="RES_NULL",
                channel="HELPLINE",
                text="Resolved but missing timestamp",
                created_at=now - timedelta(days=2)
            )
            session.add(raw_null)
            t_null = TriagedComplaint(
                complaint_id="RES_NULL",
                department="DEPT_ELEC",
                processing_status="RESOLVED",
                resolved_at=None  # Missing
            )
            session.add(t_null)
            session.commit()

            digest_null = self.weekly_digest_service.generate_weekly_digest(session, days_back=7)
            dept_elec = next(d for d in digest_null.departments if d.department == "DEPT_ELEC")
            self.assertIsNone(dept_elec.median_resolution_hours)

            # Now add 3 resolved complaints with 10h, 20h, 30h resolution times
            for idx, hours in enumerate([10, 20, 30]):
                cid = f"RES_TIME_{idx}"
                c_created = now - timedelta(hours=hours + 5)
                c_resolved = c_created + timedelta(hours=hours)
                session.add(RawComplaint(
                    complaint_id=cid,
                    channel="CITIZEN_APP",
                    text=f"Issue resolved in {hours}h",
                    created_at=c_created
                ))
                session.add(TriagedComplaint(
                    complaint_id=cid,
                    department="DEPT_RDS",
                    processing_status="RESOLVED",
                    resolved_at=c_resolved
                ))
            session.commit()

            digest_res = self.weekly_digest_service.generate_weekly_digest(session, days_back=7)
            dept_rds = next(d for d in digest_res.departments if d.department == "DEPT_RDS")
            self.assertIsNotNone(dept_rds.median_resolution_hours)
            self.assertEqual(dept_rds.median_resolution_hours, 20.0)

    # 5. repeat locality aggregation
    def test_05_repeat_locality_aggregation(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # Create a cluster in Ward 12
            cluster = DuplicateCluster(
                cluster_id="CLUS_WARD12",
                summary="Indira Nagar Potholes",
                confidence=0.92,
                detection_method="multi_signal_weighted",
                department="DEPT_RDS",
                canonical_locality="Indira Nagar",
                ward="12"
            )
            session.add(cluster)
            session.flush()

            # Add 2 complaints in cluster
            for i in range(1, 3):
                cid = f"COMP_W12_{i}"
                session.add(RawComplaint(
                    complaint_id=cid,
                    channel="HELPLINE",
                    text=f"Pothole {i} Indira Nagar",
                    created_at=now - timedelta(days=1)
                ))
                session.add(TriagedComplaint(
                    complaint_id=cid,
                    department="DEPT_RDS",
                    normalized_locality="Indira Nagar",
                    ward="12",
                    zone="Zone 2",
                    duplicate_cluster_id="CLUS_WARD12"
                ))
                session.add(ClusterMember(
                    cluster_id="CLUS_WARD12",
                    complaint_id=cid,
                    similarity_score=0.92
                ))

            # Add 1 singleton complaint in Ward 12
            cid_single = "COMP_W12_SINGLE"
            session.add(RawComplaint(
                complaint_id=cid_single,
                channel="HELPLINE",
                text="Streetlight broken",
                created_at=now - timedelta(days=2)
            ))
            session.add(TriagedComplaint(
                complaint_id=cid_single,
                department="DEPT_RDS",
                normalized_locality="Indira Nagar",
                ward="12",
                zone="Zone 2"
            ))
            session.commit()

            stats = self.repeat_locality_service.get_repeat_localities(session, days_back=7)
            self.assertGreater(len(stats.localities), 0)
            w12 = next(s for s in stats.localities if s.ward == "12")
            self.assertEqual(w12.total_complaints, 3)
            self.assertEqual(w12.unique_clusters, 2)  # 1 multi-complaint cluster + 1 singleton
            self.assertEqual(w12.repeat_complaints, 1)   # 3 - 2 = 1 repeat report

    # 6. cluster ranking
    def test_06_cluster_ranking(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # Cluster B with 5 members for DEPT_RDS
            cluster_b = DuplicateCluster(
                cluster_id="CLUS_B",
                summary="Huge road crater",
                confidence=0.95,
                detection_method="multi_signal_weighted",
                department="DEPT_RDS",
                created_at=now - timedelta(days=2)
            )
            session.add(cluster_b)
            session.flush()

            for i in range(1, 6):
                session.add(RawComplaint(complaint_id=f"B{i}", channel="APP", text="Road", created_at=now - timedelta(days=2)))
                session.add(TriagedComplaint(complaint_id=f"B{i}", department="DEPT_RDS", duplicate_cluster_id="CLUS_B"))
                session.add(ClusterMember(cluster_id="CLUS_B", complaint_id=f"B{i}", similarity_score=0.95))
            session.commit()

            digest = self.weekly_digest_service.generate_weekly_digest(session, days_back=7)
            dept_rds = next(d for d in digest.departments if d.department == "DEPT_RDS")
            self.assertGreaterEqual(len(dept_rds.major_clusters), 1)
            self.assertEqual(dept_rds.major_clusters[0].cluster_id, "CLUS_B")
            self.assertEqual(dept_rds.major_clusters[0].complaint_count, 5)

    # 7. emerging alert baseline calculation
    def test_07_emerging_alert_baseline_calculation(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # Baseline period (72h to 144h ago): 2 complaints for DEPT_RDS
            for i in range(2):
                cid = f"BASE_{i}"
                session.add(RawComplaint(
                    complaint_id=cid,
                    channel="APP",
                    text="Baseline road pothole",
                    created_at=now - timedelta(hours=100)
                ))
                session.add(TriagedComplaint(
                    complaint_id=cid,
                    department="DEPT_RDS",
                    category="CAT_ROAD_MAINTENANCE",
                    normalized_locality="Indira Nagar",
                    ward="04"
                ))

            # Recent period (0h to 72h ago): 6 complaints for DEPT_RDS (3x baseline)
            for i in range(6):
                cid = f"REC_{i}"
                session.add(RawComplaint(
                    complaint_id=cid,
                    channel="APP",
                    text="Recent road pothole",
                    created_at=now - timedelta(hours=20)
                ))
                session.add(TriagedComplaint(
                    complaint_id=cid,
                    department="DEPT_RDS",
                    category="CAT_ROAD_MAINTENANCE",
                    normalized_locality="Indira Nagar",
                    ward="04"
                ))
            session.commit()

            alerts_resp = self.emerging_alerts_service.detect_emerging_issues(session)
            self.assertGreaterEqual(alerts_resp.total_alerts, 1)
            rds_alert = next((a for a in alerts_resp.alerts if a.department == "DEPT_RDS"), None)
            self.assertIsNotNone(rds_alert)
            self.assertEqual(rds_alert.baseline_count, 2)
            self.assertEqual(rds_alert.recent_count, 6)
            self.assertAlmostEqual(rds_alert.spike_multiplier, 3.0, places=1)

    # 8. emerging alert threshold
    def test_08_emerging_alert_threshold(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # Baseline: 1 complaint, Recent: 4 complaints (surge = 4.0 >= 2.0 and count = 4 >= 3)
            session.add(RawComplaint(complaint_id="B1", channel="APP", text="leak", created_at=now - timedelta(hours=90)))
            session.add(TriagedComplaint(complaint_id="B1", department="DEPT_WSS", category="CAT_WATER_SUPPLY", normalized_locality="Civil Lines", ward="02"))

            for i in range(4):
                cid = f"R{i}"
                session.add(RawComplaint(complaint_id=cid, channel="APP", text="leak", created_at=now - timedelta(hours=10)))
                session.add(TriagedComplaint(complaint_id=cid, department="DEPT_WSS", category="CAT_WATER_SUPPLY", normalized_locality="Civil Lines", ward="02"))
            session.commit()

            alerts_resp = self.emerging_alerts_service.detect_emerging_issues(session)
            self.assertTrue(any(a.department == "DEPT_WSS" for a in alerts_resp.alerts))

    # 9. no false alert below threshold
    def test_09_no_false_alert_below_threshold(self):
        now = datetime.now(timezone.utc)
        with self.SessionLocal() as session:
            # Baseline: 2 complaints, Recent: 2 complaints (count < min_recent_complaints 3, surge = 1.0 < 2.0)
            for i in range(2):
                session.add(RawComplaint(complaint_id=f"B_ELEC_{i}", channel="APP", text="light", created_at=now - timedelta(hours=90)))
                session.add(TriagedComplaint(complaint_id=f"B_ELEC_{i}", department="DEPT_ELEC", category="CAT_STREET_LIGHTING", normalized_locality="Model Town", ward="07"))
                session.add(RawComplaint(complaint_id=f"R_ELEC_{i}", channel="APP", text="light", created_at=now - timedelta(hours=10)))
                session.add(TriagedComplaint(complaint_id=f"R_ELEC_{i}", department="DEPT_ELEC", category="CAT_STREET_LIGHTING", normalized_locality="Model Town", ward="07"))
            session.commit()

            alerts_resp = self.emerging_alerts_service.detect_emerging_issues(session)
            self.assertFalse(any(a.department == "DEPT_ELEC" for a in alerts_resp.alerts))

    # 10. held-out test import
    def test_10_held_out_test_import(self):
        benchmark_path = BACKEND_DIR.parent / "data" / "test" / "benchmark_held_out_30.csv"
        records = self.evaluation_service.load_ground_truth(benchmark_path)
        self.assertEqual(len(records), 30)
        self.assertEqual(records[0]["complaint_id"], "CMP-TEST-001")
        self.assertTrue("ground_truth_department" in records[0])
        self.assertTrue("ground_truth_urgency" in records[0])

    # 11. department accuracy
    def test_11_department_accuracy(self):
        with self.SessionLocal() as session:
            # Seed 3 dummy complaints for benchmark eval
            for i in range(1, 4):
                cid = f"BENCH_{i:03d}"
                session.add(RawComplaint(complaint_id=cid, channel="APP", text="Pothole"))
                session.add(TriagedComplaint(
                    complaint_id=cid,
                    department="DEPT_RDS",
                    category="CAT_ROAD_MAINTENANCE",
                    urgency="CRITICAL" if i == 1 else "HIGH",
                    ward="04" if i == 1 else "12"
                ))
            session.commit()

            # Provide small ground truth subset
            ground_truth = [
                {"complaint_id": "BENCH_001", "ground_truth_dept": "DEPT_RDS", "ground_truth_category": "CAT_ROAD_MAINTENANCE", "ground_truth_urgency": "CRITICAL", "ground_truth_ward": "04"},
                {"complaint_id": "BENCH_002", "ground_truth_dept": "DEPT_RDS", "ground_truth_category": "CAT_ROAD_MAINTENANCE", "ground_truth_urgency": "HIGH", "ground_truth_ward": "12"},
                {"complaint_id": "BENCH_003", "ground_truth_dept": "DEPT_WSS", "ground_truth_category": "CAT_WATER_SUPPLY", "ground_truth_urgency": "CRITICAL", "ground_truth_ward": "12"},
            ]
            result = self.evaluation_service.evaluate_predictions(session, ground_truth, dataset_name="Test Subset")
            # 2 out of 3 match DEPT_RDS
            self.assertAlmostEqual(result.department_accuracy, 2.0 / 3.0, places=2)

    # 12. category accuracy
    def test_12_category_accuracy(self):
        with self.SessionLocal() as session:
            session.add(RawComplaint(complaint_id="CAT_TEST_1", channel="APP", text="Water"))
            session.add(TriagedComplaint(complaint_id="CAT_TEST_1", department="DEPT_WSS", category="CAT_WATER_SUPPLY"))
            session.commit()

            ground_truth = [
                {"complaint_id": "CAT_TEST_1", "ground_truth_dept": "DEPT_WSS", "ground_truth_category": "CAT_WATER_SUPPLY", "ground_truth_urgency": "MEDIUM", "ground_truth_ward": "12"}
            ]
            result = self.evaluation_service.evaluate_predictions(session, ground_truth)
            self.assertEqual(result.category_accuracy, 1.0)

    # 13. urgency accuracy/agreement
    def test_13_urgency_accuracy_and_agreement(self):
        with self.SessionLocal() as session:
            for cid, urg in [("URG_1", "HIGH"), ("URG_2", "LOW")]:
                session.add(RawComplaint(complaint_id=cid, channel="APP", text="Test"))
                session.add(TriagedComplaint(complaint_id=cid, department="DEPT_RDS", urgency=urg))
            session.commit()

            ground_truth = [
                {"complaint_id": "URG_1", "ground_truth_dept": "DEPT_RDS", "ground_truth_urgency": "HIGH"},
                {"complaint_id": "URG_2", "ground_truth_dept": "DEPT_RDS", "ground_truth_urgency": "MEDIUM"},  # mismatch
            ]
            result = self.evaluation_service.evaluate_predictions(session, ground_truth)
            self.assertEqual(result.urgency_accuracy, 0.5)

    # 14. locality accuracy
    def test_14_locality_accuracy(self):
        with self.SessionLocal() as session:
            for cid, ward in [("LOC_1", "04"), ("LOC_2", "12")]:
                session.add(RawComplaint(complaint_id=cid, channel="APP", text="Locality"))
                session.add(TriagedComplaint(complaint_id=cid, department="DEPT_RDS", ward=ward))
            session.commit()

            ground_truth = [
                {"complaint_id": "LOC_1", "ground_truth_dept": "DEPT_RDS", "ground_truth_ward": "04"},
                {"complaint_id": "LOC_2", "ground_truth_dept": "DEPT_RDS", "ground_truth_ward": "04"},  # mismatch
            ]
            result = self.evaluation_service.evaluate_predictions(session, ground_truth)
            self.assertEqual(result.locality_normalization_accuracy, 0.5)

    # 15. duplicate reduction metric
    def test_15_duplicate_reduction(self):
        # 10 complaints grouped into 6 clusters -> reduction is (1 - 6/10) * 100 = 40.0%
        metric = self.evaluation_service.compute_duplicate_reduction(total_complaints=10, unique_clusters=6)
        self.assertEqual(metric, 40.0)

        # 10 complaints in 10 unique singletons -> reduction is 0.0%
        metric_zero = self.evaluation_service.compute_duplicate_reduction(total_complaints=10, unique_clusters=10)
        self.assertEqual(metric_zero, 0.0)

    # 16. confusion matrix generation
    def test_16_confusion_matrix_generation(self):
        y_true = ["DEPT_RDS", "DEPT_RDS", "DEPT_WSS", "DEPT_ELEC"]
        y_pred = ["DEPT_RDS", "DEPT_WSS", "DEPT_WSS", "DEPT_ELEC"]
        classes = ["DEPT_RDS", "DEPT_WSS", "DEPT_ELEC"]

        cm_data = self.evaluation_service.compute_confusion_matrix(y_true, y_pred, classes)
        self.assertEqual(cm_data.classes, classes)
        # Check matrix row counts
        # Row 0 (DEPT_RDS): true count 2 -> pred RDS=1, pred WSS=1, pred ELEC=0
        self.assertEqual(cm_data.matrix[0], [1, 1, 0])
        # Normalized: 0.5, 0.5, 0.0
        self.assertEqual(cm_data.normalized_matrix[0], [0.5, 0.5, 0.0])

    # 17. no fabricated metrics
    def test_17_no_fabricated_metrics(self):
        # When evaluating an empty or mismatched set, metrics must be truthful numbers computed from records
        with self.SessionLocal() as session:
            result = self.evaluation_service.evaluate_predictions(session, ground_truth=[], dataset_name="Empty Test")
            self.assertEqual(result.total_samples, 0)
            self.assertEqual(result.department_accuracy, 0.0)
            self.assertEqual(result.category_accuracy, 0.0)
            self.assertFalse(result.incorrect_predictions)

    # 18. synthetic-data labeling
    def test_18_synthetic_data_labeling(self):
        with self.SessionLocal() as session:
            result = self.evaluation_service.evaluate_predictions(session, ground_truth=[], is_synthetic=True)
            self.assertTrue(result.is_synthetic_benchmark)
            self.assertIn("DEMO / SYNTHETIC BENCHMARK", result.benchmark_badge)
            self.assertIn("[PROTOTYPE_ASSUMPTION]", result.disclaimer)

    # 19. report API
    def test_19_weekly_digest_api(self):
        # Seed 1 complaint
        with self.SessionLocal() as session:
            session.add(RawComplaint(complaint_id="API_COMP_1", channel="APP", text="Broken light"))
            session.add(TriagedComplaint(
                complaint_id="API_COMP_1",
                department="DEPT_ELEC",
                ward="07",
                urgency="MEDIUM",
                processing_status="OPERATOR_REVIEW_PENDING"
            ))
            session.commit()

        response = self.client.get("/api/v1/analytics/weekly-digest?days_back=7")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["overall_received"], 1)
        self.assertIn("departments", data)
        self.assertIn("operational_summary", data)

        # Test repeat localities endpoint
        rep_resp = self.client.get("/api/v1/analytics/repeat-localities?days_back=7")
        self.assertEqual(rep_resp.status_code, 200)
        self.assertIn("localities", rep_resp.json())

        # Test emerging alerts endpoint
        alert_resp = self.client.get("/api/v1/analytics/emerging-alerts")
        self.assertEqual(alert_resp.status_code, 200)
        self.assertIn("alerts", alert_resp.json())

    # 20. evaluation API
    def test_20_evaluation_benchmark_api(self):
        # Run benchmark evaluation API against 30 held-out complaints
        response = self.client.post("/api/v1/eval/benchmark", json={
            "test_set_file": "benchmark_held_out_30.csv",
            "test_set_version": "v1.0-synthetic",
            "is_synthetic": True
        })
        self.assertEqual(response.status_code, 200)
        eval_data = response.json()
        self.assertEqual(eval_data["total_samples"], 30)
        self.assertTrue(eval_data["is_synthetic_benchmark"])
        self.assertIn("DEMO / SYNTHETIC BENCHMARK", eval_data["benchmark_badge"])
        self.assertIn("confusion_matrix", eval_data)

        # Verify get latest evaluation endpoint
        latest_resp = self.client.get("/api/v1/eval/latest")
        self.assertEqual(latest_resp.status_code, 200)
        latest_data = latest_resp.json()
        self.assertEqual(latest_data["id"], eval_data["id"])


if __name__ == "__main__":
    unittest.main()
