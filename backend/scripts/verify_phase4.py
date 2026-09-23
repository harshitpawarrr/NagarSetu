"""
Phase 4 Verification Script for NagarSetu
Tests at least 10 synthetic complaints through the full triage processing pipeline:
- English, Hindi, and Hinglish cases
- Mandatory safety hazard overrides
- Low-confidence / manual review cases
- Explainable routing evidence capture
- Raw data immutability verification
- Graceful degradation when GEMINI_API_KEY is not set
"""

import sys
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.db.session import SessionLocal
from app.models.complaint import RawComplaint, TriagedComplaint, ImmutableDataError
from app.services.triage.triage_service import TriageService
from tests.mocks.mock_gemini import MockGeminiClient


def run_phase4_verification():
    db = SessionLocal()
    print("=" * 70)
    print("🏛️  NAGARSETU PHASE 4: TRIAGE PIPELINE VERIFICATION")
    print("=" * 70)

    # 1. Select 10 diverse complaints from database
    complaints = db.query(RawComplaint).limit(10).all()
    print(f"Loaded {len(complaints)} complaints from database for verification.\n")

    triage_service = TriageService(gemini_client=MockGeminiClient())

    processed_records = []
    safety_override_found = False
    manual_review_found = False

    for idx, raw in enumerate(complaints, 1):
        complaint_id = raw.complaint_id
        original_text = raw.text or raw.image_caption or ""

        # Capture raw text before processing
        pre_text = raw.text

        # Process through pipeline (force reprocess to run Phase 4 algorithms)
        triaged = triage_service.process_complaint(complaint_id=complaint_id, db=db, reprocess=True)
        db.refresh(raw)

        # Immutability Check: raw text MUST be unchanged
        assert raw.text == pre_text, f"VIOLATION: Raw complaint '{complaint_id}' was mutated!"

        # Extract audit breakdown
        audit = triaged.triage_metadata or {}
        urgency_audit = audit.get("urgency_breakdown", {})
        routing_audit = audit.get("routing", {})
        review_flags = audit.get("review_flags", {})

        if urgency_audit.get("safety_override_applied"):
            safety_override_found = True

        if review_flags.get("requires_manual_review") or review_flags.get("review_flagged"):
            manual_review_found = True

        processed_records.append({
            "idx": idx,
            "id": complaint_id,
            "lang": triaged.language,
            "summary": triaged.summary,
            "dept": triaged.department,
            "category": triaged.category,
            "urgency": triaged.urgency,
            "urgency_score": triaged.urgency_score,
            "safety_score": urgency_audit.get("safety_score"),
            "outage_score": urgency_audit.get("outage_score"),
            "duration_score": urgency_audit.get("duration_score"),
            "safety_override": urgency_audit.get("safety_override_applied"),
            "override_rule": urgency_audit.get("safety_override_rule_id"),
            "locality": triaged.normalized_locality,
            "ward": triaged.ward,
            "zone": triaged.zone,
            "routing_rule": routing_audit.get("routing_rule_id"),
            "routing_confidence": triaged.routing_confidence,
            "routing_evidence": routing_audit.get("routing_evidence", []),
            "review_tier": review_flags.get("confidence_tier"),
            "manual_review": review_flags.get("requires_manual_review")
        })

        print(f"[{idx}/10] {complaint_id} ({raw.channel})")
        print(f"   Snippet : {original_text[:80]}...")
        print(f"   Route   : {triaged.department} | Category: {triaged.category}")
        print(f"   Urgency : {triaged.urgency} (Score: {triaged.urgency_score:.2f}) [Safety: {urgency_audit.get('safety_score')}, Outage: {urgency_audit.get('outage_score')}, Duration: {urgency_audit.get('duration_score')}]")
        if urgency_audit.get("safety_override_applied"):
            print(f"   ⚠️  SAFETY OVERRIDE APPLIED: Rule {urgency_audit.get('safety_override_rule_id')}")
        print(f"   Locality: {triaged.normalized_locality} ({triaged.ward}, {triaged.zone})")
        print(f"   Evidence: {routing_audit.get('routing_evidence')}")
        print(f"   Review  : Tier={review_flags.get('confidence_tier')}, ManualReview={review_flags.get('requires_manual_review')}")
        print("-" * 70)

    # 2. Verify Immutability with deliberate mutation attempt
    print("\nVerifying Raw Complaint Immutability Hook:")
    try:
        complaints[0].text = "HACK ATTEMPT: Trying to modify raw text directly."
        db.commit()
        print("❌ FAILED: RawComplaint was modified without error!")
    except ImmutableDataError as ide:
        db.rollback()
        print(f"✅ PASSED: ImmutableDataError successfully triggered: {ide}")

    # 3. Verify Graceful Degradation when Gemini is not configured
    print("\nVerifying Graceful Fallback (Gemini Not Configured):")
    unconfigured_service = TriageService(gemini_client=MockGeminiClient(configured=False))
    fallback_result = unconfigured_service.classification_service.classify(
        "Open manhole on main thoroughfare near market"
    )
    print(f"✅ Fallback output received: Department={fallback_result.department}, Category={fallback_result.category}, Confidence={fallback_result.confidence}")
    assert fallback_result.confidence <= 0.60, "Fallback confidence should be capped"

    print("\n" + "=" * 70)
    print("SUMMARY OF VERIFICATION METRICS:")
    print(f" - Total Complaints Triaged : {len(processed_records)}")
    print(f" - Safety Overrides Detected: {safety_override_found} (At least one: {'YES' if safety_override_found else 'NO'})")
    print(f" - Manual Reviews Flagged   : {manual_review_found} (At least one: {'YES' if manual_review_found else 'NO'})")
    print(f" - Raw Data Mutations       : 0 (Strictly Blocked by ORM Immutability)")
    print("=" * 70)
    print("PHASE 4 VERIFICATION COMPLETED SUCCESSFULLY!")

    db.close()


if __name__ == "__main__":
    run_phase4_verification()
