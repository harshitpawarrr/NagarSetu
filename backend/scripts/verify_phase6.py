"""
Phase 6 End-to-End Verification Script for NagarSetu:
Weekly Departmental Digest, Cluster Analytics, Emerging Alerts, and Held-Out Benchmark Evaluation.
"""

import sys
import json
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure UTF-8 stdout for Devanagari Hindi text on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.db.session import SessionLocal
from app.services.analytics.weekly_digest_service import WeeklyDigestService
from app.services.analytics.repeat_locality_service import RepeatLocalityService
from app.services.analytics.emerging_alerts_service import EmergingAlertsService
from app.services.evaluation.evaluation_service import EvaluationService
from app.schemas.evaluation import EvaluationRunRequest


def main():
    print("=" * 80)
    print(" NAGARSETU PHASE 6 VERIFICATION: DIGESTS, ANALYTICS & HELD-OUT EVALUATION")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 1. Weekly Digest Verification
        print("\n[STEP 1] Generating Weekly Departmental Accountability Digest...")
        digest_service = WeeklyDigestService()
        digest = digest_service.generate_weekly_digest(db, days_back=7, persist=True)

        print(f"  Period: {digest.report_period_start} to {digest.report_period_end}")
        print(f"  Overall Received: {digest.overall_received}")
        print(f"  Overall Resolved: {digest.overall_resolved}")
        print(f"  Overall Pending:  {digest.overall_pending}")
        print(f"  Overall Median Resolution Time: {digest.overall_median_resolution_hours} hours")
        print(f"  Disclaimer: {digest.disclaimer}")
        print("\n  Departmental Breakdown:")
        for d in digest.departments:
            print(f"    - [{d.department}] {d.department_name or 'N/A'}: Received={d.complaints_received}, Resolved={d.complaints_resolved}, Pending={d.complaints_pending}, MedianSLA={d.median_resolution_hours}h, HighUrgencyOpen={d.high_urgency_unresolved}")
            if d.top_categories:
                cats_str = ", ".join([f"{c.category} ({c.count})" for c in d.top_categories[:3]])
                print(f"      Top Categories: {cats_str}")

        # 2. Repeat Localities Verification
        print("\n[STEP 2] Aggregating Repeat Complaints by Locality & Ward...")
        repeat_service = RepeatLocalityService()
        rep_resp = repeat_service.get_repeat_localities(db, days_back=30)
        print(f"  Total Locality/Ward Groups Analyzed: {len(rep_resp.localities)}")
        print(f"  Total Repeat Complaints: {rep_resp.total_repeat_complaints}")
        print("  Top Hotspots:")
        for loc in rep_resp.localities[:5]:
            print(f"    - {loc.locality} (Ward {loc.ward or 'N/A'}, {loc.department or 'General'}): Total={loc.total_complaints}, UniqueIssues={loc.unique_clusters}, Repeats={loc.repeat_complaints}, RepeatRate={loc.repeat_rate_pct}%")

        # 3. Emerging Issue Alerts Verification
        print("\n[STEP 3] Evaluating Emerging Issue Early-Warning Heuristic...")
        alerts_service = EmergingAlertsService()
        alerts_resp = alerts_service.detect_emerging_issues(db)
        print(f"  Total Active Volume Surge Alerts: {alerts_resp.total_alerts}")
        print(f"  Evaluated At: {alerts_resp.evaluation_timestamp.isoformat()}")
        for a in alerts_resp.alerts[:5]:
            print(f"    - ALERT [{a.alert_id}]: Dept={a.department}, Ward={a.ward or 'N/A'}, Locality={a.locality}")
            print(f"      Surge: {a.recent_count} recent vs {a.baseline_count} baseline (Spike Factor: {a.spike_multiplier:.1f}x)")
            print(f"      Trigger: {a.trigger_explanation}")
            print(f"      Disclaimer: {a.heuristic_disclaimer}")

        # 4. Held-Out Test Set Formal Evaluation
        print("\n[STEP 4] Executing Formal Benchmark on Held-Out Test Set (30 samples)...")
        eval_service = EvaluationService()
        eval_run_req = EvaluationRunRequest(
            test_set_file="benchmark_held_out_30.csv",
            test_set_version="v1.0-synthetic",
            is_synthetic=True,
            notes="Formal Phase 6 Held-Out Evaluation Verification Run"
        )
        eval_res = eval_service.run_evaluation(db, eval_run_req)

        print("\n" + "=" * 80)
        print(" HELD-OUT TEST SET EVALUATION SCORECARD")
        print("=" * 80)
        print(f"  Dataset: {eval_res.test_set_version} ({eval_res.total_samples} samples)")
        print(f"  Badge:   [{eval_res.benchmark_badge}]")
        print(f"  Department Routing Accuracy:  {eval_res.department_accuracy * 100:.1f}%")
        print(f"  Category Accuracy:            {eval_res.category_accuracy * 100:.1f}%")
        print(f"  Urgency Agreement:            {eval_res.urgency_accuracy * 100:.1f}%")
        print(f"  Locality Normalization Acc:   {eval_res.locality_normalization_accuracy * 100:.1f}%")
        print(f"  Duplicate Volume Reduction:   {eval_res.duplicate_reduction:.1f}%")
        print(f"  Truthfulness Disclaimer:      {eval_res.disclaimer}")

        if eval_res.confusion_matrix:
            print("\n  Department Confusion Matrix (Counts & Row-Normalized Recall):")
            classes = eval_res.confusion_matrix.classes
            header = f"{'True \\ Pred':<12}" + "".join([f"{c:>11}" for c in classes])
            print("  " + header)
            print("  " + "-" * len(header))
            for i, c in enumerate(classes):
                row_str = f"{c:<12}" + "".join([f"{eval_res.confusion_matrix.matrix[i][j]:>11}" for j in range(len(classes))])
                print("  " + row_str)

        if eval_res.incorrect_predictions:
            print(f"\n  Auditable Misclassifications Inspection (Showing first {len(eval_res.incorrect_predictions[:3])}):")
            for mis in eval_res.incorrect_predictions[:3]:
                print(f"    - [{mis.complaint_id}] Field '{mis.field}': True='{mis.ground_truth}' vs Pred='{mis.predicted}' (Conf: {mis.confidence})")
                print(f"      Text: \"{mis.text_snippet}\"")

        print("\n" + "=" * 80)
        print(" [OK] PHASE 6 VERIFICATION COMPLETED SUCCESSFULLY")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
