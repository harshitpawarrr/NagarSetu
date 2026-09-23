"""
Exhaustive Test Suite for NagarSetu Phase 5:
Duplicate / Incident Cluster Detection and Operator Decision Desk.
Verifies all 23 required test scenarios:
1. Obvious duplicate complaints
2. Hindi/English duplicate pair
3. Hinglish/English duplicate pair
4. Same issue from different channels
5. Same category but different locations
6. Same location but different issue
7. Temporal separation
8. False positive prevention
9. Cluster creation
10. Cluster membership
11. Duplicate reduction metric
12. Operator approval
13. Department override
14. Category override
15. Urgency override
16. Locality correction
17. Audit history
18. Acknowledgement draft
19. Acknowledgement edit
20. Acknowledgement approval
21. Raw data immutability after operator actions
22. Cluster review API
23. Complaint review API
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
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory, ImmutableDataError
from app.models.cluster import DuplicateCluster, ClusterMember
from app.models.audit import ComplaintAudit
from app.models.acknowledgement import Acknowledgement
from app.services.clustering.similarity_engine import SimilarityEngine
from app.services.clustering.cluster_service import ClusterService
from app.services.operator.operator_service import OperatorService
from app.schemas.operator import (
    OperatorReviewRequest,
    AcknowledgementEditRequest,
    AcknowledgementApproveRequest
)
from app.main import app
from app.db.session import get_db


class TestClusteringAndOperatorDesk(unittest.TestCase):
    """
    Comprehensive test suite validating Phase 5 clustering algorithms,
    operator workflows, audit logging, and API endpoints.
    """

    @classmethod
    def setUpClass(cls):
        # In-memory SQLite for testing with StaticPool to share state across sessions
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        create_tables(bind_engine=cls.engine)

        # Seed basic taxonomy
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

        cls.similarity_engine = SimilarityEngine()
        cls.cluster_service = ClusterService(similarity_engine=cls.similarity_engine)
        cls.operator_service = OperatorService()

        # Configure API TestClient
        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    # =========================================================================
    # PART A: SIMILARITY SIGNALS & MULTILINGUAL MATCHING (Tests 1-8)
    # =========================================================================

    def test_01_obvious_duplicate_complaints(self):
        """Test obvious duplicate complaints with nearly identical text at same locality."""
        c1 = {
            "complaint_id": "CMP-01-A",
            "text": "Large pothole in front of City School main gate",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
            "routing_terms": ["pothole", "road"]
        }
        c2 = {
            "complaint_id": "CMP-01-B",
            "text": "Huge dangerous pothole near City School gate",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 11, 30, tzinfo=timezone.utc),
            "routing_terms": ["pothole", "dangerous"]
        }
        score, signals, rel_type = self.similarity_engine.compute_similarity(c1, c2)
        self.assertGreaterEqual(score, 0.72)
        self.assertEqual(rel_type, "LIKELY_DUPLICATE")
        self.assertEqual(signals["category"], 1.0)
        self.assertEqual(signals["ward"], 1.0)

    def test_02_hindi_english_duplicate_pair(self):
        """Test Hindi Devanagari and English duplicate pair reporting the same civic issue."""
        c_en = {
            "complaint_id": "CMP-02-EN",
            "text": "Big pothole on main road near City School MP Nagar",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
            "routing_terms": ["pothole"]
        }
        c_hi = {
            "complaint_id": "CMP-02-HI",
            "text": "सिटी स्कूल के पास एमपी नगर में बड़ा गड्ढा है सड़क पर",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc),
            "routing_terms": ["gaddha", "गड्ढा"]
        }
        score, signals, rel_type = self.similarity_engine.compute_similarity(c_en, c_hi)
        self.assertGreaterEqual(score, 0.70)
        self.assertIn(rel_type, ["LIKELY_DUPLICATE", "RELATED_INCIDENT"])
        self.assertGreaterEqual(signals["semantic_text"], 0.60)

    def test_03_hinglish_english_duplicate_pair(self):
        """Test Hinglish transliteration and English duplicate pair."""
        c_en = {
            "complaint_id": "CMP-03-EN",
            "text": "Road damaged with large pothole outside City School",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 9, 0, tzinfo=timezone.utc)
        }
        c_hinglish = {
            "complaint_id": "CMP-03-HG",
            "text": "City School ke paas bada gaddha hai road toot gayi hai",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 9, 45, tzinfo=timezone.utc)
        }
        score, signals, rel_type = self.similarity_engine.compute_similarity(c_en, c_hinglish)
        self.assertGreaterEqual(score, 0.70)
        self.assertIn(rel_type, ["LIKELY_DUPLICATE", "RELATED_INCIDENT"])

    def test_04_same_issue_different_channels(self):
        """Test that same issue reported via different channels (e.g. municipal app vs helpline) matches cleanly."""
        c_app = {
            "complaint_id": "CMP-04-APP",
            "text": "Streetlight pole sparking and dark near Clock Tower",
            "department": "DEPT_ELEC",
            "category": "CAT_STREET_LIGHTING",
            "normalized_locality": "Gandhi Chowk",
            "ward": "Ward 102",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc),
            "channel": "municipal_app"
        }
        c_helpline = {
            "complaint_id": "CMP-04-HLP",
            "text": "Dark street light at Clock Tower not working",
            "department": "DEPT_ELEC",
            "category": "CAT_STREET_LIGHTING",
            "normalized_locality": "Gandhi Chowk",
            "ward": "Ward 102",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc),
            "channel": "state_helpline"
        }
        score, _, rel_type = self.similarity_engine.compute_similarity(c_app, c_helpline)
        self.assertGreaterEqual(score, 0.72)
        self.assertEqual(rel_type, "LIKELY_DUPLICATE")

    def test_05_same_category_different_locations(self):
        """Test false positive prevention: same issue category in completely different wards."""
        c_mp_nagar = {
            "complaint_id": "CMP-05-MP",
            "text": "Huge pothole on main road",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        c_civil_lines = {
            "complaint_id": "CMP-05-CL",
            "text": "Huge pothole on main road",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "Civil Lines",
            "ward": "Ward 301",
            "zone": "North Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        score, signals, rel_type = self.similarity_engine.compute_similarity(c_mp_nagar, c_civil_lines)
        self.assertLess(score, 0.50)  # Capped by ward mismatch sanity rule
        self.assertEqual(rel_type, "NO_MATCH")

    def test_06_same_location_different_issue(self):
        """Test false positive prevention: same locality but completely different departments/issues."""
        c_manhole = {
            "complaint_id": "CMP-06-WSS",
            "text": "Open sewer manhole cover missing",
            "department": "DEPT_WSS",
            "category": "CAT_WATER_SUPPLY",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        c_garbage = {
            "complaint_id": "CMP-06-SWM",
            "text": "Overflowing garbage dustbin with stray dogs",
            "department": "DEPT_SWM",
            "category": "CAT_GARBAGE_COLLECTION",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        score, _, rel_type = self.similarity_engine.compute_similarity(c_manhole, c_garbage)
        self.assertLess(score, 0.40)
        self.assertEqual(rel_type, "NO_MATCH")

    def test_07_temporal_separation(self):
        """Test temporal decay: same issue and location separated by 14 days decays similarity."""
        c_today = {
            "complaint_id": "CMP-07-NOW",
            "text": "Pothole on main road",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        c_old = {
            "complaint_id": "CMP-07-OLD",
            "text": "Pothole on main road",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)  # 14 days earlier
        }
        score, signals, rel_type = self.similarity_engine.compute_similarity(c_today, c_old)
        self.assertLessEqual(signals["temporal"], 0.10)
        self.assertLess(score, 0.72)  # Cannot be classified as active LIKELY_DUPLICATE

    def test_08_false_positive_prevention(self):
        """Test completely divergent complaints produce NO_MATCH."""
        c_light = {
            "complaint_id": "CMP-08-A",
            "text": "Streetlight pole broken near station",
            "department": "DEPT_ELEC",
            "category": "CAT_STREET_LIGHTING",
            "normalized_locality": "Railway Station",
            "ward": "Ward 10",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        c_dog = {
            "complaint_id": "CMP-08-B",
            "text": "Aggressive stray dogs chasing two wheelers",
            "department": "DEPT_SWM",
            "category": "CAT_GARBAGE_COLLECTION",
            "normalized_locality": "Vasant Vihar",
            "ward": "Ward 201",
            "zone": "South Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        }
        score, _, rel_type = self.similarity_engine.compute_similarity(c_light, c_dog)
        self.assertLess(score, 0.30)
        self.assertEqual(rel_type, "NO_MATCH")

    # =========================================================================
    # PART B: CLUSTER SERVICE, MEMBERSHIP & REDUCTION ANALYTICS (Tests 9-11)
    # =========================================================================

    def test_09_cluster_creation(self):
        """Test automated creation of DuplicateCluster from triaged complaints."""
        # Seed 2 duplicate complaints
        rc1 = RawComplaint(complaint_id="CMP-TEST-CL-1", channel="municipal_app", text="Large pothole near City School", timestamp=datetime.now(timezone.utc))
        rc2 = RawComplaint(complaint_id="CMP-TEST-CL-2", channel="state_helpline", text="Dangerous deep pothole near City School gate", timestamp=datetime.now(timezone.utc))
        self.db.add_all([rc1, rc2])
        self.db.flush()

        tc1 = TriagedComplaint(
            complaint_id="CMP-TEST-CL-1",
            summary="Large pothole near City School",
            department="DEPT_RDS",
            category="CAT_ROAD_MAINTENANCE",
            urgency="MEDIUM",
            normalized_locality="MP Nagar",
            ward="Ward 42",
            zone="Central Zone"
        )
        tc2 = TriagedComplaint(
            complaint_id="CMP-TEST-CL-2",
            summary="Dangerous pothole near City School gate",
            department="DEPT_RDS",
            category="CAT_ROAD_MAINTENANCE",
            urgency="MEDIUM",
            normalized_locality="MP Nagar",
            ward="Ward 42",
            zone="Central Zone"
        )
        self.db.add_all([tc1, tc2])
        self.db.commit()

        res = self.cluster_service.detect_clusters(self.db, recluster=True)
        self.assertTrue(res.success)
        self.assertGreaterEqual(res.clusters_created, 1)

        cluster = self.db.query(DuplicateCluster).first()
        self.assertIsNotNone(cluster)
        self.assertEqual(cluster.department, "DEPT_RDS")
        self.assertEqual(cluster.ward, "Ward 42")
        self.assertTrue(cluster.is_active)

    def test_10_cluster_membership(self):
        """Test that cluster members are recorded with similarity scores and audit linkage."""
        cluster = self.db.query(DuplicateCluster).first()
        self.assertIsNotNone(cluster)

        members = self.db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster.cluster_id).all()
        self.assertGreaterEqual(len(members), 2)
        for m in members:
            self.assertIsNotNone(m.similarity_score)
            self.assertIn(m.relationship_type, ["LIKELY_DUPLICATE", "RELATED_INCIDENT"])
            self.assertTrue(m.is_confirmed)

        # Verify triaged records link back
        tc1 = self.db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertEqual(tc1.duplicate_cluster_id, cluster.cluster_id)

    def test_11_duplicate_reduction_metric(self):
        """Test accurate calculation of ticket reduction percentage according to formula."""
        analytics = self.cluster_service.compute_analytics(self.db)
        self.assertGreater(analytics.raw_complaint_count, 0)
        self.assertGreaterEqual(analytics.ticket_reduction_percentage, 0.0)
        # Check formula consistency
        expected_unique = analytics.unique_cluster_count + analytics.unclustered_complaint_count
        self.assertEqual(analytics.unique_issue_count, expected_unique)
        self.assertIn("[PROTOTYPE_ASSUMPTION]", analytics.disclaimer)

    # =========================================================================
    # PART C: OPERATOR REVIEWS, OVERRIDES & AUDIT HISTORY (Tests 12-17)
    # =========================================================================

    def test_12_operator_approval(self):
        """Test operator approval transitions status to OPERATOR_APPROVED without modifying raw record."""
        req = OperatorReviewRequest(
            action="approve",
            operator_id="OP-DESK-42",
            notes="AI recommendations verified by operator."
        )
        res = self.operator_service.review_complaint(self.db, "CMP-TEST-CL-1", req)
        self.assertTrue(res.success)
        self.assertEqual(res.processing_status, "OPERATOR_APPROVED")

        tc = self.db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertEqual(tc.processing_status, "OPERATOR_APPROVED")
        self.assertIsNotNone(tc.operator_decision)

    def test_13_department_override(self):
        """Test operator overriding department creates audit entry and separates AI rec from decision."""
        req = OperatorReviewRequest(
            action="override",
            department="DEPT_WSS",
            reason="Water leakage causing road erosion, re-routing to WSS.",
            operator_id="OP-DESK-42"
        )
        res = self.operator_service.review_complaint(self.db, "CMP-TEST-CL-1", req)
        self.assertTrue(res.success)

        tc = self.db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertEqual(tc.department, "DEPT_WSS")
        self.assertIn("department", tc.operator_overrides)
        self.assertEqual(tc.operator_overrides["department"]["override"], "DEPT_WSS")

    def test_14_category_override(self):
        """Test operator category override."""
        req = OperatorReviewRequest(
            action="override",
            category="CAT_WATER_SUPPLY",
            reason="Reclassified to water supply issue.",
            operator_id="OP-DESK-42"
        )
        res = self.operator_service.review_complaint(self.db, "CMP-TEST-CL-1", req)
        self.assertTrue(res.success)
        tc = self.db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertEqual(tc.category, "CAT_WATER_SUPPLY")

    def test_15_urgency_override(self):
        """Test operator urgency escalation override."""
        req = OperatorReviewRequest(
            action="override",
            urgency="CRITICAL",
            reason="School proximity presents severe public hazard.",
            operator_id="OP-DESK-42"
        )
        res = self.operator_service.review_complaint(self.db, "CMP-TEST-CL-1", req)
        self.assertTrue(res.success)
        tc = self.db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertEqual(tc.urgency, "CRITICAL")

    def test_16_locality_correction(self):
        """Test operator correcting locality and ward."""
        req = OperatorReviewRequest(
            action="override",
            normalized_locality="MP Nagar Zone 1",
            ward="Ward 42",
            reason="Corrected to specific Zone 1 landmark.",
            operator_id="OP-DESK-42"
        )
        res = self.operator_service.review_complaint(self.db, "CMP-TEST-CL-1", req)
        self.assertTrue(res.success)
        tc = self.db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertEqual(tc.normalized_locality, "MP Nagar Zone 1")

    def test_17_audit_history(self):
        """Test complete chronological audit trail retrieval."""
        trail = self.operator_service.get_audit_trail(self.db, "CMP-TEST-CL-1")
        self.assertGreaterEqual(len(trail), 4)  # approval, dept override, cat override, urgency override, locality override
        fields = [t.field_changed for t in trail]
        self.assertIn("department", fields)
        self.assertIn("category", fields)
        self.assertIn("urgency", fields)
        self.assertIn("normalized_locality", fields)

    # =========================================================================
    # PART D: CITIZEN ACKNOWLEDGEMENT APPROVAL WORKFLOW (Tests 18-20)
    # =========================================================================

    def test_18_acknowledgement_draft(self):
        """Test retrieval of draft citizen acknowledgement."""
        ack = self.operator_service.get_acknowledgement(self.db, "CMP-TEST-CL-1")
        self.assertIsNotNone(ack)
        self.assertEqual(ack.status, "draft")
        self.assertIn("CMP-TEST-CL-1", ack.draft_text)

    def test_19_acknowledgement_edit(self):
        """Test operator editing draft text transitions status to 'edited'."""
        req = AcknowledgementEditRequest(
            draft_text="Dear Citizen, your complaint regarding the road issue near City School is under inspection.",
            language="en",
            operator_id="OP-DESK-42"
        )
        ack = self.operator_service.edit_acknowledgement(self.db, "CMP-TEST-CL-1", req)
        self.assertEqual(ack.status, "edited")
        self.assertIn("City School is under inspection", ack.draft_text)
        self.assertIsNotNone(ack.edited_at)

    def test_20_acknowledgement_approval(self):
        """Test operator approval of acknowledgement (strictly internal sign-off, no external dispatch)."""
        req = AcknowledgementApproveRequest(
            operator_id="OP-DESK-42",
            notes="Sign-off verified for internal records."
        )
        ack = self.operator_service.approve_acknowledgement(self.db, "CMP-TEST-CL-1", req)
        self.assertEqual(ack.status, "approved")
        self.assertEqual(ack.approved_by, "OP-DESK-42")
        self.assertIsNotNone(ack.approved_at)
        self.assertIn("[NO_EXTERNAL_DISPATCH]", ack.disclaimer)

    # =========================================================================
    # PART E: IMMUTABILITY & API CONTRACTS (Tests 21-23)
    # =========================================================================

    def test_21_raw_data_immutability_after_operator_actions(self):
        """Verify that RawComplaint records remain strictly immutable despite all operator overrides."""
        raw = self.db.query(RawComplaint).filter(RawComplaint.complaint_id == "CMP-TEST-CL-1").first()
        self.assertIsNotNone(raw)

        # Attempt to mutate raw complaint text
        with self.assertRaises(ImmutableDataError):
            raw.text = "Tampered text body"
            self.db.flush()
        self.db.rollback()

    def test_22_cluster_review_api(self):
        """Test POST /api/v1/clusters/{cluster_id}/review to remove member and add notes."""
        cluster = self.db.query(DuplicateCluster).first()
        self.assertIsNotNone(cluster)

        # Add operator notes
        res = self.client.post(f"/api/v1/clusters/{cluster.cluster_id}/review", json={
            "action": "add_notes",
            "notes": "Verified by municipal supervisor.",
            "operator_id": "OP-ZONE-42"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])

        # Remove member
        res_rm = self.client.post(f"/api/v1/clusters/{cluster.cluster_id}/review", json={
            "action": "remove_member",
            "complaint_id": "CMP-TEST-CL-2",
            "operator_id": "OP-ZONE-42",
            "notes": "Separate incident, removed from cluster."
        })
        self.assertEqual(res_rm.status_code, 200)

    def test_23_complaint_review_api(self):
        """Test POST /api/v1/complaints/{id}/review API endpoint."""
        res = self.client.post("/api/v1/complaints/CMP-TEST-CL-2/review", json={
            "action": "approve",
            "operator_id": "OP-ZONE-42",
            "notes": "Approved via API client."
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["processing_status"], "OPERATOR_APPROVED")


if __name__ == "__main__":
    unittest.main()
