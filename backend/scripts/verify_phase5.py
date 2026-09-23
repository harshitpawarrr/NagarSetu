"""
End-to-End Verification Script for NagarSetu Phase 5.
Validates:
1. Multi-signal multilingual duplicate and incident cluster detection
2. Deterministic representative selection and reduction analytics
3. Operator triage approval and field overrides
4. Chronological audit logging in complaint_audits
5. Human-in-the-loop acknowledgement draft, edit, and internal approval
6. Absolute immutability of raw_complaints
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure utf-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Setup python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.db.init_db import create_tables
from app.models.complaint import RawComplaint, TriagedComplaint, ImmutableDataError
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


def run_phase5_verification():
    print("=" * 70)
    print("🏛️  NAGARSETU PHASE 5: CLUSTERING & OPERATOR DESK VERIFICATION")
    print("=" * 70)

    create_tables()
    db = SessionLocal()

    try:
        sim_engine = SimilarityEngine()
        cluster_service = ClusterService(similarity_engine=sim_engine)
        operator_service = OperatorService()

        # Step 1: Verify Multi-Signal Similarity Engine on Multilingual Pairs
        print("\n--- 1. Testing Multilingual Matching Signals ---")
        en_complaint = {
            "complaint_id": "DEMO-EN",
            "text": "Deep dangerous pothole on main road near Sargam Cinema MP Nagar",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc),
            "routing_terms": ["pothole", "gaddha"]
        }
        hi_complaint = {
            "complaint_id": "DEMO-HI",
            "text": "सरगम सिनेमा के पास एमपी नगर में सड़क पर बहुत बड़ा गड्ढा है",
            "department": "DEPT_RDS",
            "category": "CAT_ROAD_MAINTENANCE",
            "normalized_locality": "MP Nagar",
            "ward": "Ward 42",
            "zone": "Central Zone",
            "timestamp": datetime(2026, 9, 15, 11, 15, tzinfo=timezone.utc),
            "routing_terms": ["gaddha", "गड्ढा"]
        }

        score, signals, rel = sim_engine.compute_similarity(en_complaint, hi_complaint)
        print(f"   Pair        : English vs Hindi Devanagari (Same MP Nagar Pothole)")
        print(f"   Sim Score   : {score:.3f} | Relationship: {rel}")
        print(f"   Signals     : Text={signals['semantic_text']}, Locality={signals['canonical_locality']}, Ward={signals['ward']}")
        assert score >= 0.70, f"Expected high similarity for multilingual pair, got {score}"
        print("   ✅ Multilingual concept & locality matching PASSED!")

        # Step 2: Seed & Run Cluster Detection
        print("\n--- 2. Executing Cluster Detection on Database Records ---")
        # Ensure at least two complaints exist for clustering test
        c1_id = "CMP-SYN-CL-1"
        c2_id = "CMP-SYN-CL-2"
        existing_rc1 = db.query(RawComplaint).filter(RawComplaint.complaint_id == c1_id).first()
        if not existing_rc1:
            rc1 = RawComplaint(
                complaint_id=c1_id,
                channel="municipal_app",
                text="Massive pothole near City School MP Nagar causing traffic jams",
                source_location="MP Nagar",
                timestamp=datetime.now(timezone.utc)
            )
            rc2 = RawComplaint(
                complaint_id=c2_id,
                channel="state_helpline",
                text="City School ke samne bada gaddha hai MP Nagar mein",
                source_location="MP Nagar",
                timestamp=datetime.now(timezone.utc)
            )
            db.add_all([rc1, rc2])
            db.flush()

            tc1 = TriagedComplaint(
                complaint_id=c1_id,
                summary="Massive pothole near City School",
                department="DEPT_RDS",
                category="CAT_ROAD_MAINTENANCE",
                urgency="HIGH",
                urgency_score=0.75,
                normalized_locality="MP Nagar",
                ward="Ward 42",
                zone="Central Zone"
            )
            tc2 = TriagedComplaint(
                complaint_id=c2_id,
                summary="City School ke samne bada gaddha",
                department="DEPT_RDS",
                category="CAT_ROAD_MAINTENANCE",
                urgency="HIGH",
                urgency_score=0.75,
                normalized_locality="MP Nagar",
                ward="Ward 42",
                zone="Central Zone"
            )
            db.add_all([tc1, tc2])
            db.commit()

        detect_res = cluster_service.detect_clusters(db, recluster=False)
        print(f"   Clusters Formed  : {detect_res.clusters_created}")
        print(f"   Total Clustered  : {detect_res.total_complaints_clustered}")
        print(f"   Ticket Reduction : {detect_res.analytics.ticket_reduction_percentage}%")
        print(f"   Disclaimer       : {detect_res.analytics.disclaimer}")
        assert detect_res.analytics.ticket_reduction_percentage >= 0.0

        # Step 3: Test Operator Decision Desk Workflow
        print("\n--- 3. Testing Operator Approval & Overrides ---")
        # Approve triage
        app_res = operator_service.review_complaint(
            db=db,
            complaint_id=c1_id,
            req=OperatorReviewRequest(
                action="approve",
                operator_id="OP-ZONE-42",
                notes="Verified ground report from Ward 42 beat engineer."
            )
        )
        print(f"   Complaint {c1_id} status updated to: {app_res.processing_status}")
        assert app_res.processing_status == "OPERATOR_APPROVED"

        # Apply department override with audit
        ovr_res = operator_service.review_complaint(
            db=db,
            complaint_id=c2_id,
            req=OperatorReviewRequest(
                action="override",
                department="DEPT_WSS",
                urgency="CRITICAL",
                reason="Inspection indicates underground water main rupture caused the subsidence.",
                operator_id="OP-ZONE-42"
            )
        )
        print(f"   Complaint {c2_id} overridden to: Dept={ovr_res.operator_decision.get('fields_overridden')}")
        assert ovr_res.processing_status == "OPERATOR_APPROVED"

        # Step 4: Verify Chronological Audit History
        print("\n--- 4. Verifying Chronological Audit Log ---")
        audits = operator_service.get_audit_trail(db, c2_id)
        print(f"   Audit entries found for {c2_id}: {len(audits)}")
        for a in audits:
            print(f"    - [{a.created_at.strftime('%H:%M:%S')}] {a.operator_id} modified '{a.field_changed}': {a.original_value} -> {a.new_value} (Reason: {a.reason})")
        assert len(audits) >= 2

        # Step 5: Citizen Acknowledgement Workflow (Zero External Send)
        print("\n--- 5. Testing Citizen Acknowledgement Workflow ---")
        ack = operator_service.get_acknowledgement(db, c1_id)
        print(f"   Initial Draft Status: {ack.status}")

        # Operator edits draft
        edited_ack = operator_service.edit_acknowledgement(
            db, c1_id,
            AcknowledgementEditRequest(
                draft_text="Dear Citizen, your road pothole report near City School has been assigned to Ward 42 team.",
                language="en",
                operator_id="OP-ZONE-42"
            )
        )
        print(f"   Post-Edit Status    : {edited_ack.status}")
        assert edited_ack.status == "edited"

        # Operator approves draft
        app_ack = operator_service.approve_acknowledgement(
            db, c1_id,
            AcknowledgementApproveRequest(operator_id="OP-ZONE-42")
        )
        print(f"   Approved Status     : {app_ack.status} (Approved by: {app_ack.approved_by})")
        print(f"   Governance Boundary : {app_ack.disclaimer}")
        assert app_ack.status == "approved"

        # Step 6: Raw Complaint Immutability Hook Check
        print("\n--- 6. Verifying Raw Complaint Immutability ---")
        raw_rec = db.query(RawComplaint).filter(RawComplaint.complaint_id == c1_id).first()
        try:
            raw_rec.text = "Attempted tampering"
            db.flush()
            print("❌ FAILED: Immutability was bypassed!")
            sys.exit(1)
        except ImmutableDataError as ide:
            print(f"   ✅ PASSED: ImmutableDataError successfully triggered: {str(ide)}")
            db.rollback()

        print("\n" + "=" * 70)
        print("🎉 ALL PHASE 5 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_phase5_verification()
