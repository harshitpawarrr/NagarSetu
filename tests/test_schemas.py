"""
Unit tests for Canonical Complaint Schema and Configuration Files
Validates that all required fields from the specification are strictly enforced.
Can be executed via standard python `unittest` or `pytest`.
"""

import unittest
import json
import sys
from pathlib import Path
from datetime import datetime, date, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError

from app.schemas.complaint import (
    CanonicalComplaint,
    ComplaintChannel,
    UrgencyLevel,
    ProcessingStatus,
    MultimodalAttachment,
    InputModality
)
from app.schemas.digest import (
    WeeklyDepartmentDigest,
    DepartmentMetric,
    LocalityRepeatStat,
    ClusterSummary
)


class TestCanonicalComplaintSchema(unittest.TestCase):

    def test_canonical_complaint_valid_instantiation(self):
        """Verify that a complaint ticket with all required fields instantiates cleanly."""
        ticket_data = {
            "complaint_id": "CMP-2026-00101",
            "original_channel": ComplaintChannel.STATE_HELPLINE,
            "original_text": "Shivaji Nagar market ke samne open manhole cover gayab hai, live wire paas me hai.",
            "language": "hi",
            "summary": "Missing manhole cover and adjacent wire near Shivaji Nagar market.",
            "department": "DEPT_WSS",
            "category": "CAT_DRAINAGE_SEWAGE",
            "subcategory": "SUB_MISSING_MANHOLE_COVER",
            "urgency": UrgencyLevel.CRITICAL,
            "urgency_score": 0.95,
            "urgency_reason": "Immediate life-safety hazard: Open manhole on active pedestrian thoroughfare.",
            "normalized_locality": "Shivaji Nagar Sector A",
            "ward": "WARD_101",
            "zone": "Central Zone",
            "duplicate_cluster_id": "CLUSTER_WARD101_MANHOLE_01",
            "duplicate_confidence": 0.92,
            "routing_evidence": "Matched sewerage keywords 'open manhole' with Category CAT_DRAINAGE_SEWAGE.",
            "routing_confidence": 0.90,
            "acknowledgement_draft": "Draft acknowledgement: Your complaint CMP-2026-00101 has been registered.",
            "created_at": datetime.now(timezone.utc),
            "processing_status": ProcessingStatus.OPERATOR_REVIEW_PENDING,
            "attachments": [
                MultimodalAttachment(
                    modality=InputModality.IMAGE_CAPTION,
                    file_uri="data/raw/sample_manhole.jpg",
                    caption="Photograph showing uncovered manhole on main road"
                )
            ]
        }
        complaint = CanonicalComplaint(**ticket_data)
        self.assertEqual(complaint.complaint_id, "CMP-2026-00101")
        self.assertEqual(complaint.urgency, UrgencyLevel.CRITICAL)
        self.assertEqual(complaint.urgency_score, 0.95)
        self.assertEqual(complaint.processing_status, ProcessingStatus.OPERATOR_REVIEW_PENDING)
        self.assertEqual(len(complaint.attachments), 1)

    def test_canonical_complaint_missing_required_fields_fails(self):
        """Verify that omitting required fields raises a validation error."""
        with self.assertRaises(ValidationError):
            # Missing department, urgency_score, routing_evidence, etc.
            CanonicalComplaint(
                complaint_id="CMP-FAIL-01",
                original_channel=ComplaintChannel.MUNICIPAL_APP,
                original_text="Some garbage issue",
                summary="Garbage issue"
            )

    def test_canonical_complaint_urgency_score_range(self):
        """Verify urgency_score must be bounded between 0.0 and 1.0."""
        base_data = {
            "complaint_id": "CMP-RANGE-TEST",
            "original_channel": ComplaintChannel.SOCIAL_MEDIA,
            "original_text": "Streetlight flickering.",
            "summary": "Streetlight flickering.",
            "department": "DEPT_ELEC",
            "category": "CAT_STREET_LIGHTING",
            "urgency": UrgencyLevel.LOW,
            "urgency_reason": "Low hazard",
            "normalized_locality": "Gandhi Chowk",
            "routing_evidence": "Streetlight keyword match",
            "routing_confidence": 0.85,
            "acknowledgement_draft": "Your report is received."
        }

        # Score > 1.0 should fail
        with self.assertRaises(ValidationError):
            CanonicalComplaint(**base_data, urgency_score=1.5)

        # Score < 0.0 should fail
        with self.assertRaises(ValidationError):
            CanonicalComplaint(**base_data, urgency_score=-0.1)

        # Score within 0.0 to 1.0 passes
        valid_complaint = CanonicalComplaint(**base_data, urgency_score=0.45)
        self.assertEqual(valid_complaint.urgency_score, 0.45)

    def test_weekly_digest_schema(self):
        """Verify WeeklyDepartmentDigest conforms to reporting requirements."""
        digest = WeeklyDepartmentDigest(
            digest_id="DIGEST-2026-W37",
            period_start_date=date(2026, 9, 8),
            period_end_date=date(2026, 9, 14),
            total_received=150,
            total_resolved=128,
            total_pending=22,
            overall_median_resolution_hours=18.5,
            departmental_metrics=[
                DepartmentMetric(
                    department_id="DEPT_SWM",
                    department_name="Solid Waste Management",
                    received_count=60,
                    resolved_count=55,
                    pending_count=5,
                    median_resolution_time_hours=12.0,
                    sla_compliance_rate=0.92
                )
            ],
            repeat_complaints_by_locality=[
                LocalityRepeatStat(
                    locality="Shivaji Nagar",
                    ward="WARD_101",
                    repeat_complaint_count=8,
                    primary_department="DEPT_SWM",
                    primary_category="CAT_GARBAGE_COLLECTION"
                )
            ],
            major_clusters=[
                ClusterSummary(
                    cluster_id="CLUST-001",
                    department="DEPT_WSS",
                    incident_count=14,
                    first_reported_at=datetime.now(timezone.utc),
                    latest_reported_at=datetime.now(timezone.utc),
                    summary="Water supply outage across Shivaji Nagar Sector B",
                    is_active=True,
                    urgency_level="HIGH"
                )
            ]
        )
        self.assertEqual(digest.total_received, 150)
        self.assertEqual(digest.total_pending, 22)
        self.assertEqual(len(digest.departmental_metrics), 1)
        self.assertEqual(len(digest.repeat_complaints_by_locality), 1)

    def test_departments_config_file(self):
        """Verify config/departments.json exists and has valid departments."""
        path = ROOT_DIR / "config" / "departments.json"
        self.assertTrue(path.exists(), "config/departments.json must exist")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("departments", data)
        self.assertGreater(len(data["departments"]), 0)
        dept_ids = [d["department_id"] for d in data["departments"]]
        self.assertIn("DEPT_SWM", dept_ids)
        self.assertIn("DEPT_WSS", dept_ids)

    def test_categories_config_file(self):
        """Verify config/categories.json exists and maps to departments."""
        path = ROOT_DIR / "config" / "categories.json"
        self.assertTrue(path.exists(), "config/categories.json must exist")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("categories", data)
        for cat in data["categories"]:
            self.assertIn("category_id", cat)
            self.assertIn("department_id", cat)
            self.assertIn("subcategories", cat)

    def test_urgency_rules_config_file(self):
        """Verify config/urgency_rules.json exists and defines deterministic rules."""
        path = ROOT_DIR / "config" / "urgency_rules.json"
        self.assertTrue(path.exists(), "config/urgency_rules.json must exist")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("rules", data)
        for rule in data["rules"]:
            self.assertIn("rule_id", rule)
            self.assertIn("enforced_urgency", rule)
            self.assertIn("urgency_score", rule)
            self.assertIn("urgency_reason", rule)

    def test_routing_rules_config_file(self):
        """Verify config/routing_rules.json exists and defines routing heuristics."""
        path = ROOT_DIR / "config" / "routing_rules.json"
        self.assertTrue(path.exists(), "config/routing_rules.json must exist")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("rules", data)
        for rule in data["rules"]:
            self.assertIn("rule_id", rule)
            self.assertIn("target_department", rule)
            self.assertIn("routing_evidence_template", rule)

    def test_gazetteer_config_file(self):
        """Verify data/gazetteer/sample_wards_gazetteer.json exists and has zones/wards."""
        path = ROOT_DIR / "data" / "gazetteer" / "sample_wards_gazetteer.json"
        self.assertTrue(path.exists(), "sample_wards_gazetteer.json must exist")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("zones", data)
        self.assertGreater(len(data["zones"]), 0)
        first_zone = data["zones"][0]
        self.assertIn("wards", first_zone)
        self.assertGreater(len(first_zone["wards"]), 0)


if __name__ == "__main__":
    unittest.main()
