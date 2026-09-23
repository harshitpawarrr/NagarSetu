import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.session import SessionLocal
from app.services.evaluation.evaluation_service import EvaluationService
from app.schemas.evaluation import EvaluationRunRequest
from app.services.ingestion.ingestion_service import IngestionService
from app.services.triage.triage_service import TriageService
import json

def run():
    db = SessionLocal()
    
    # 1. Ingest and process benchmark data so it exists in DB
    print("Ingesting and processing benchmark dataset...")
    ingest = IngestionService(db)
    triage = TriageService()
    benchmark_path = Path("data/test/benchmark_held_out_30.csv")
    
    summary = ingest.ingest_csv_file(benchmark_path)
    print(f"Ingestion complete.")
    import csv
    with open(benchmark_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cids = [row["complaint_id"] for row in reader]
    
    # Triage them
    processed = 0
    for cid in cids:
        # TriageService is already idempotent
        triage.process_complaint(cid, db)
        processed += 1
    
    print(f"Processed {processed} new complaints through triage pipeline.")

    eval_service = EvaluationService()
    records = eval_service.load_ground_truth(benchmark_path)
    res = eval_service.evaluate_predictions(db, records, dataset_name="v1.0-synthetic", is_synthetic=True)
    
    print("\n" + "="*50)
    print("EVALUATION RESULTS")
    print("="*50)
    
    print(f"Total Samples: {res.total_samples}")
    print(f"\n[RAW METRICS] (Using ground truth literally)")
    print(f"  Raw Department Accuracy: {res.raw_department_accuracy * 100:.1f}%")
    print(f"  Raw Category Accuracy:   {res.raw_category_accuracy * 100:.1f}%")
    
    print(f"\n[DIAGNOSTIC METRICS] (Accounting for aliases & ground-truth taxonomy contradiction)")
    print(f"  Diagnostic Dept Accuracy: {res.diagnostic_department_accuracy * 100:.1f}%")
    print(f"  Diagnostic Cat Accuracy:  {res.diagnostic_category_accuracy * 100:.1f}%")
    
    print(f"\n[OTHER METRICS]")
    print(f"  Urgency Accuracy:       {res.urgency_accuracy * 100:.1f}%")
    print(f"  Locality Norm Accuracy: {res.locality_normalization_accuracy * 100:.1f}%")
    print(f"  Duplicate Reduction:    {res.duplicate_reduction:.1f}%")
    
    print(f"\n[TAXONOMY CONTRADICTION FLAGS IN GROUND TRUTH]")
    for flag in res.taxonomy_consistency_flags:
        print(f"  - [{flag.complaint_id}] {flag.reason}")
        
    print(f"\n[DIAGNOSTIC CHANGES APPLIED]")
    for change in res.diagnostic_changes:
        print(f"  - [{change.complaint_id} / {change.field}] {change.original_gt} -> {change.canonical_pred} | {change.reason}")
    
    db.close()

if __name__ == "__main__":
    run()
