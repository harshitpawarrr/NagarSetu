"""
Phase 4 Triage Pipeline Unit & Integration Test Suite
Verifies all 22 required test cases:
1. English classification
2. Hindi classification
3. Hinglish classification
4. Valid structured AI output
5. Malformed AI response handling
6. Missing AI fields handling
7. Invalid department/category taxonomy validation
8. Low-confidence output review flagging
9. Deterministic safety overrides
10. Non-safety urgency scoring
11. Duration scoring
12. Service outage scoring
13. Locality normalization integration
14. Correct explainable routing
15. Unknown routing fallback
16. Routing explanation generation
17. Routing evidence capture
18. Raw data immutability during and after triage
19. Reprocessing and idempotency
20. API process endpoint
21. API triage retrieval endpoint
22. API reprocess endpoint
"""

import os
import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup system path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.base import Base
from app.db.init_db import create_tables
from app.db.session import get_db
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory, ImmutableDataError
from app.models.taxonomy import Department, Category
from app.models.gazetteer import LocalityGazetteer, LocalityAlias
from app.schemas.triage import AIClassificationResult, UrgencyEvaluationResult, ExplainableRoutingResult
from app.schemas.complaint import UrgencyLevel, ProcessingStatus
from app.services.classification.classifier import ClassificationService
from app.rules.urgency_engine import UrgencyEngine
from app.rules.locality_normalizer import LocalityNormalizer
from app.rules.routing_engine import RoutingEngine
from app.rules.confidence_evaluator import ConfidenceEvaluator
from app.services.triage.triage_service import TriageService
from app.main import app
from tests.mocks.mock_gemini import MockGeminiClient

TEST_DB_PATH = ROOT_DIR / "data" / "test_triage.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestTriagePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass

        create_tables(bind_engine=test_engine)
        from app.api.triage import get_triage_service
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_triage_service] = lambda: TriageService(gemini_client=MockGeminiClient())
        cls.client = TestClient(app)

        # Seed reference taxonomy and gazetteer into test db
        db = TestingSessionLocal()
        from scripts.seed_data import seed_departments, seed_categories, seed_gazetteer
        dept_map = seed_departments(db)
        seed_categories(db, dept_map)
        seed_gazetteer(db)
        db.close()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass

    def setUp(self):
        self.db = TestingSessionLocal()

    def tearDown(self):
        self.db.close()

    def _create_sample_raw(self, complaint_id: str, text: str, channel: str = "municipal_app", loc: str = None) -> RawComplaint:
        """Helper to create an immutable RawComplaint."""
        raw = self.db.query(RawComplaint).filter_by(complaint_id=complaint_id).first()
        if not raw:
            raw = RawComplaint(
                complaint_id=complaint_id,
                channel=channel,
                text=text,
                source_location=loc,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(raw)
            # Add initial PREPROCESSED triaged record
            triaged = TriagedComplaint(
                complaint_id=complaint_id,
                processing_status="PREPROCESSED"
            )
            self.db.add(triaged)
            self.db.commit()
            self.db.refresh(raw)
        return raw

    # -------------------------------------------------------------
    # 1. English Classification
    # -------------------------------------------------------------
    def test_01_english_classification(self):
        mock_client = MockGeminiClient()
        classifier = ClassificationService(client=mock_client)
        result = classifier.classify("MP Nagar street lights non-functional for 4 days")
        self.assertEqual(result.department, "DEPT_ELEC")
        self.assertEqual(result.category, "CAT_STREET_LIGHTING")
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertIn("street light", [t.lower() for t in result.routing_terms])

    # -------------------------------------------------------------
    # 2. Hindi Classification
    # -------------------------------------------------------------
    def test_02_hindi_classification(self):
        mock_client = MockGeminiClient()
        classifier = ClassificationService(client=mock_client)
        result = classifier.classify("शिवाजी नगर सेक्टर A में गंदा पानी आ रहा है")
        self.assertEqual(result.language, "hi")
        self.assertEqual(result.department, "DEPT_WSS")
        self.assertEqual(result.category, "CAT_WATER_SUPPLY")
        self.assertGreaterEqual(result.confidence, 0.85)

    # -------------------------------------------------------------
    # 3. Hinglish Classification
    # -------------------------------------------------------------
    def test_03_hinglish_classification(self):
        mock_client = MockGeminiClient()
        classifier = ClassificationService(client=mock_client)
        result = classifier.classify("Ward 12 mein bada pothole hai")
        self.assertIn(result.language, ["hi-Latn", "hi", "en"])
        self.assertEqual(result.department, "DEPT_RDS")
        self.assertEqual(result.category, "CAT_ROAD_MAINTENANCE")
        self.assertGreaterEqual(result.confidence, 0.85)

    # -------------------------------------------------------------
    # 4. Valid Structured AI Output
    # -------------------------------------------------------------
    def test_04_valid_structured_ai_output(self):
        mock_client = MockGeminiClient()
        classifier = ClassificationService(client=mock_client)
        result = classifier.classify("Overflowing garbage bin near market")
        self.assertIsInstance(result, AIClassificationResult)
        self.assertTrue(hasattr(result, "language"))
        self.assertTrue(hasattr(result, "summary"))
        self.assertTrue(hasattr(result, "department"))
        self.assertTrue(hasattr(result, "category"))
        self.assertTrue(hasattr(result, "subcategory"))
        self.assertTrue(hasattr(result, "routing_terms"))
        self.assertTrue(hasattr(result, "confidence"))
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    # -------------------------------------------------------------
    # 5. Malformed AI Response Handling
    # -------------------------------------------------------------
    def test_05_malformed_ai_response(self):
        mock_client = MockGeminiClient(mode="malformed_json")
        classifier = ClassificationService(client=mock_client)
        # Should gracefully fall back to keyword classification without throwing unhandled exception
        result = classifier.classify("Pothole on main road")
        self.assertIsInstance(result, AIClassificationResult)
        self.assertEqual(result.department, "DEPT_RDS")
        self.assertEqual(result.category, "CAT_ROAD_MAINTENANCE")

    # -------------------------------------------------------------
    # 6. Missing AI Fields Handling
    # -------------------------------------------------------------
    def test_06_missing_ai_fields(self):
        mock_client = MockGeminiClient(mode="missing_fields")
        classifier = ClassificationService(client=mock_client)
        # Should recover gracefully via fallback
        result = classifier.classify("Street light not working in Sector B")
        self.assertIsInstance(result, AIClassificationResult)
        self.assertEqual(result.department, "DEPT_ELEC")

    # -------------------------------------------------------------
    # 7. Invalid Department / Category Taxonomy Validation
    # -------------------------------------------------------------
    def test_07_invalid_department_category(self):
        mock_client = MockGeminiClient(mode="invalid_taxonomy")
        classifier = ClassificationService(client=mock_client)
        result = classifier.classify("Street light broken")
        # Should detect invalid taxonomy and clamp confidence to <= 0.35
        self.assertLessEqual(result.confidence, 0.35)
        self.assertTrue(any("MISMATCH" in t for t in result.routing_terms))

    # -------------------------------------------------------------
    # 8. Low-Confidence Output Review Flagging
    # -------------------------------------------------------------
    def test_08_low_confidence_output(self):
        evaluator = ConfidenceEvaluator()
        review_flags = evaluator.evaluate(
            classification_confidence=0.42,
            routing_confidence=0.45
        )
        self.assertTrue(review_flags.requires_manual_review)
        self.assertTrue(review_flags.review_flagged)
        self.assertEqual(review_flags.confidence_tier, "MANUAL_REVIEW")
        self.assertIn("Manual review required", review_flags.review_reason)

    # -------------------------------------------------------------
    # 9. Deterministic Safety Overrides
    # -------------------------------------------------------------
    def test_09_safety_override(self):
        urgency_engine = UrgencyEngine()
        # Live electrical wire sparking
        result = urgency_engine.evaluate("Live wire sparking near school gate, major shock risk")
        self.assertEqual(result.urgency, UrgencyLevel.CRITICAL)
        self.assertTrue(result.safety_override_applied)
        self.assertEqual(result.safety_override_rule_id, "URG_RULE_001")
        self.assertGreaterEqual(result.urgency_score, 0.95)

        # Missing open manhole
        result2 = urgency_engine.evaluate("Missing manhole cover open manhole on dark road")
        self.assertEqual(result2.urgency, UrgencyLevel.CRITICAL)
        self.assertTrue(result2.safety_override_applied)
        self.assertEqual(result2.safety_override_rule_id, "URG_RULE_002")

    # -------------------------------------------------------------
    # 10. Non-Safety Urgency Scoring
    # -------------------------------------------------------------
    def test_10_non_safety_urgency_scoring(self):
        urgency_engine = UrgencyEngine()
        result = urgency_engine.evaluate("Routine garbage paper litter dry waste sweeping needed")
        self.assertEqual(result.urgency, UrgencyLevel.LOW)
        self.assertFalse(result.safety_override_applied)
        self.assertLess(result.safety_score, 20)
        self.assertLessEqual(result.urgency_score, 0.40)
        self.assertTrue(hasattr(result, "safety_score"))
        self.assertTrue(hasattr(result, "outage_score"))
        self.assertTrue(hasattr(result, "duration_score"))

    # -------------------------------------------------------------
    # 11. Duration Scoring
    # -------------------------------------------------------------
    def test_11_duration_scoring(self):
        urgency_engine = UrgencyEngine()
        result_prolonged = urgency_engine.evaluate("Water tap not working for 2 months already")
        result_short = urgency_engine.evaluate("Water tap not working since today morning")
        self.assertGreater(result_prolonged.duration_score, result_short.duration_score)
        self.assertGreaterEqual(result_prolonged.duration_score, 25)

    # -------------------------------------------------------------
    # 12. Service Outage Scoring
    # -------------------------------------------------------------
    def test_12_service_outage_scoring(self):
        urgency_engine = UrgencyEngine()
        result_area = urgency_engine.evaluate("Complete blackout in entire colony, all houses dark")
        result_single = urgency_engine.evaluate("One street light bulb flickering")
        self.assertGreater(result_area.outage_score, result_single.outage_score)
        self.assertGreaterEqual(result_area.outage_score, 22)

    # -------------------------------------------------------------
    # 13. Locality Normalization Integration
    # -------------------------------------------------------------
    def test_13_locality_normalization_integration(self):
        normalizer = LocalityNormalizer()
        # Substring alias match
        result = normalizer.normalize(
            source_location_hint=None,
            complaint_text="Sargam Cinema ke samne MP Nagar mein road kharab hai",
            db=self.db
        )
        self.assertEqual(result.canonical_locality, "MP Nagar")
        self.assertEqual(result.ward, "Ward 42")
        self.assertEqual(result.zone, "Central Zone")
        self.assertIn(result.match_type, ["alias_match", "landmark_match"])

        # Unknown locality
        unknown_result = normalizer.normalize(
            source_location_hint=None,
            complaint_text="Random unspecified location with no landmark",
            db=self.db
        )
        self.assertEqual(unknown_result.canonical_locality, "UNKNOWN")
        self.assertIsNone(unknown_result.ward)
        self.assertEqual(unknown_result.confidence, 0.0)

    # -------------------------------------------------------------
    # 14. Correct Routing
    # -------------------------------------------------------------
    def test_14_correct_routing(self):
        routing_engine = RoutingEngine()
        result = routing_engine.route(
            predicted_department="DEPT_RDS",
            category_id="CAT_ROAD_MAINTENANCE",
            routing_terms=["pothole", "gaddha"],
            complaint_text="Big pothole on road"
        )
        self.assertEqual(result.recommended_department, "DEPT_RDS")
        self.assertEqual(result.routing_rule_id, "ROUTE_RULE_RDS_01")
        self.assertGreaterEqual(result.routing_confidence, 0.85)

    # -------------------------------------------------------------
    # 15. Unknown Routing Fallback
    # -------------------------------------------------------------
    def test_15_unknown_routing(self):
        routing_engine = RoutingEngine()
        result = routing_engine.route(
            predicted_department="DEPT_UNKNOWN_XYZ",
            category_id="CAT_UNKNOWN_ABC",
            routing_terms=["unclear"],
            complaint_text="Vague unintelligible text"
        )
        self.assertEqual(result.recommended_department, "DEPT_SWM")  # default fallback
        self.assertEqual(result.routing_rule_id, "ROUTE_UNKNOWN_FALLBACK")
        self.assertLessEqual(result.routing_confidence, 0.50)

    # -------------------------------------------------------------
    # 16. Routing Explanation Generation
    # -------------------------------------------------------------
    def test_16_routing_explanation(self):
        routing_engine = RoutingEngine()
        result = routing_engine.route(
            predicted_department="DEPT_ELEC",
            category_id="CAT_STREET_LIGHTING",
            routing_terms=["streetlight", "bijli"],
            complaint_text="Streetlight not working"
        )
        self.assertIsInstance(result.routing_explanation, str)
        self.assertGreater(len(result.routing_explanation), 15)
        self.assertIn("Electrical", result.routing_explanation)

    # -------------------------------------------------------------
    # 17. Routing Evidence Capture
    # -------------------------------------------------------------
    def test_17_routing_evidence(self):
        routing_engine = RoutingEngine()
        result = routing_engine.route(
            predicted_department="DEPT_ELEC",
            category_id="CAT_STREET_LIGHTING",
            routing_terms=["streetlight"],
            complaint_text="Dark road streetlight out"
        )
        self.assertIsInstance(result.routing_evidence, list)
        self.assertGreaterEqual(len(result.routing_evidence), 1)

    # -------------------------------------------------------------
    # 18. Raw Data Immutability
    # -------------------------------------------------------------
    def test_18_raw_data_immutability(self):
        raw = self._create_sample_raw("CMP-TEST-IMMUTABLE-01", "Initial raw complaint text")
        service = TriageService(gemini_client=MockGeminiClient())
        triaged = service.process_complaint(complaint_id="CMP-TEST-IMMUTABLE-01", db=self.db)

        # Verify raw complaint remains identical
        self.db.refresh(raw)
        self.assertEqual(raw.text, "Initial raw complaint text")

        # Verify raw complaint cannot be updated
        raw.text = "Tampered text"
        with self.assertRaises(ImmutableDataError):
            self.db.commit()
        self.db.rollback()

    # -------------------------------------------------------------
    # 19. Reprocessing and Idempotency
    # -------------------------------------------------------------
    def test_19_reprocessing_idempotency(self):
        raw = self._create_sample_raw("CMP-TEST-IDEM-01", "Pothole in MP Nagar road")
        service = TriageService(gemini_client=MockGeminiClient())

        # First processing
        t1 = service.process_complaint("CMP-TEST-IDEM-01", self.db, reprocess=False)
        processed_at_1 = t1.processed_at

        # Second processing without reprocess flag -> should return existing without re-triage
        t2 = service.process_complaint("CMP-TEST-IDEM-01", self.db, reprocess=False)
        self.assertEqual(t1.id, t2.id)
        self.assertEqual(t1.processed_at, t2.processed_at)

        # Reprocessing with reprocess=True
        t3 = service.process_complaint("CMP-TEST-IDEM-01", self.db, reprocess=True)
        self.assertEqual(t1.id, t3.id)
        self.assertGreaterEqual(t3.processed_at, processed_at_1)

    # -------------------------------------------------------------
    # 20. API Process Endpoint
    # -------------------------------------------------------------
    def test_20_api_process_endpoint(self):
        raw = self._create_sample_raw("CMP-API-PROC-01", "Shivaji Nagar sector A me tap se ganda peela paani aa raha hai")
        response = self.client.post("/api/v1/complaints/CMP-API-PROC-01/process")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["complaint_id"], "CMP-API-PROC-01")
        self.assertEqual(data["department"], "DEPT_WSS")
        self.assertIn("triage_audit", data)
        self.assertEqual(data["processing_status"], "OPERATOR_REVIEW_PENDING")

    # -------------------------------------------------------------
    # 21. API Triage Retrieval Endpoint
    # -------------------------------------------------------------
    def test_21_api_triage_retrieval(self):
        # Process first
        self._create_sample_raw("CMP-API-TRIAGE-01", "Huge pothole in MP Nagar near Sargam Cinema")
        self.client.post("/api/v1/complaints/CMP-API-TRIAGE-01/process")

        # Now retrieve triage details
        response = self.client.get("/api/v1/complaints/CMP-API-TRIAGE-01/triage")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["complaint_id"], "CMP-API-TRIAGE-01")
        self.assertEqual(data["department"], "DEPT_RDS")
        self.assertEqual(data["normalized_locality"], "MP Nagar")
        audit = data["triage_audit"]
        self.assertIn("urgency_breakdown", audit)
        self.assertIn("safety_score", audit["urgency_breakdown"])
        self.assertIn("routing", audit)

    # -------------------------------------------------------------
    # 22. API Reprocess Endpoint
    # -------------------------------------------------------------
    def test_22_api_reprocess_endpoint(self):
        self._create_sample_raw("CMP-API-REPROC-01", "Street lights dark in MP Nagar for 4 days")
        res1 = self.client.post("/api/v1/complaints/CMP-API-REPROC-01/process")
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/v1/complaints/CMP-API-REPROC-01/reprocess")
        self.assertEqual(res2.status_code, 200)
        data = res2.json()
        self.assertEqual(data["complaint_id"], "CMP-API-REPROC-01")
        self.assertEqual(data["department"], "DEPT_ELEC")


if __name__ == "__main__":
    unittest.main()
