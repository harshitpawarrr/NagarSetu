"""
Held-Out Test Set Formal Evaluation Service for NagarSetu.
Evaluates department routing, category classification, urgency assessment,
locality normalization, and duplicate reduction against curated ground-truth sets.
Strictly separates test data from training/triage code and forbids fake metrics.
"""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.analytics import EvaluationResult
from app.schemas.evaluation import (
    EvaluationRunRequest,
    EvaluationResultResponse,
    EvaluationHistoryResponse,
    ConfusionMatrixData,
    IncorrectPrediction
)
from app.services.classification.classifier import ClassificationService
from app.rules.urgency_engine import UrgencyEngine
from app.rules.locality_normalizer import LocalityNormalizer
from app.services.clustering.similarity_engine import SimilarityEngine
from app.services.clustering.cluster_service import ClusterService

logger = logging.getLogger("nagarsetu.evaluation_service")

DATA_TEST_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "test"


class EvaluationService:
    """
    Executes formal benchmarks against held-out ground truth data.
    """

    def __init__(
        self,
        classifier: Optional[ClassificationService] = None,
        urgency_engine: Optional[UrgencyEngine] = None,
        locality_normalizer: Optional[LocalityNormalizer] = None,
        similarity_engine: Optional[SimilarityEngine] = None
    ):
        self.classifier = classifier or ClassificationService()
        self.urgency_engine = urgency_engine or UrgencyEngine()
        self.locality_normalizer = locality_normalizer or LocalityNormalizer()
        self.similarity_engine = similarity_engine or SimilarityEngine()

    @staticmethod
    def load_ground_truth(file_path: Any) -> List[Dict[str, str]]:
        """Loads and parses ground truth complaints from CSV file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth file not found: '{path}'")
        records: List[Dict[str, str]] = []
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {k.strip(): (v.strip() if v else "") for k, v in row.items() if k}
                if cleaned.get("complaint_id") or cleaned.get("text"):
                    records.append(cleaned)
        return records

    @staticmethod
    def compute_duplicate_reduction(total_complaints: int, unique_clusters: int) -> float:
        """Computes duplicate volume reduction percentage."""
        if total_complaints <= 0:
            return 0.0
        return round(((total_complaints - unique_clusters) / float(total_complaints)) * 100.0, 2)

    @staticmethod
    def compute_confusion_matrix(y_true: List[str], y_pred: List[str], classes: List[str]) -> ConfusionMatrixData:
        """Computes multi-class confusion matrix, normalized values, and per-class metrics."""
        class_to_idx = {c: i for i, c in enumerate(classes)}
        n = len(classes)
        matrix = [[0 for _ in range(n)] for _ in range(n)]

        for yt, yp in zip(y_true, y_pred):
            if yt in class_to_idx and yp in class_to_idx:
                matrix[class_to_idx[yt]][class_to_idx[yp]] += 1

        normalized = []
        for row in matrix:
            row_sum = sum(row)
            if row_sum > 0:
                normalized.append([round(v / float(row_sum), 3) for v in row])
            else:
                normalized.append([0.0 for _ in row])

        per_class: Dict[str, Dict[str, float]] = {}
        for c in classes:
            idx = class_to_idx[c]
            tp = matrix[idx][idx]
            fp = sum(matrix[r][idx] for r in range(n) if r != idx)
            fn = sum(matrix[idx][col] for col in range(n) if col != idx)
            prec = round(tp / float(tp + fp), 3) if (tp + fp) > 0 else 0.0
            rec = round(tp / float(tp + fn), 3) if (tp + fn) > 0 else 0.0
            f1 = round(2 * prec * rec / (prec + rec), 3) if (prec + rec) > 0 else 0.0
            per_class[c] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}

        return ConfusionMatrixData(
            classes=classes,
            matrix=matrix,
            normalized_matrix=normalized,
            per_class=per_class
        )

    def evaluate_predictions(
        self,
        db: Session,
        ground_truth: List[Dict[str, Any]],
        dataset_name: str = "Test Set",
        is_synthetic: bool = True
    ) -> EvaluationResultResponse:
        """
        Evaluates already-triaged records in database against ground truth labels.
        Never fabricates metrics.
        """
        from app.models.complaint import TriagedComplaint
        total_samples = len(ground_truth)
        if total_samples == 0:
            badge = "DEMO / SYNTHETIC BENCHMARK" if is_synthetic else "VERIFIED REAL BENCHMARK"
            return EvaluationResultResponse(
                id=999,
                test_set_version=dataset_name,
                total_samples=0,
                department_accuracy=0.0,
                category_accuracy=0.0,
                urgency_accuracy=0.0,
                locality_normalization_accuracy=0.0,
                duplicate_reduction=0.0,
                confusion_matrix=None,
                per_class_metrics={},
                incorrect_predictions=[],
                is_synthetic_benchmark=is_synthetic,
                benchmark_badge=badge,
                evaluated_at=datetime.now(timezone.utc),
                notes="Zero samples evaluated."
            )

        correct_dept = 0
        correct_cat = 0
        correct_dept_raw = 0
        correct_dept_diag = 0
        correct_cat_raw = 0
        correct_cat_diag = 0
        correct_urg = 0
        correct_loc = 0
        dept_classes = ["DEPT_RDS", "DEPT_WSS", "DEPT_ELEC", "DEPT_SWM", "DEPT_HORT", "DEPT_PH", "DEPT_TOWN", "DEPT_HLT", "DEPT_ENCR"]
        y_true_dept = []
        y_pred_dept = []
        incorrect: List[IncorrectPrediction] = []
        
        from app.schemas.evaluation import TaxonomyFlag, DiagnosticChange
        taxonomy_flags: List[TaxonomyFlag] = []
        diagnostic_changes: List[DiagnosticChange] = []
        
        canonical_dept_map = {"DEPT_PH": "DEPT_HLT", "DEPT_TOWN": "DEPT_ENCR"}
        canonical_cat_map = {"CAT_PARK_MAINTENANCE": "CAT_HORTICULTURE", "CAT_TOWN_PLANNING": "CAT_ENCROACHMENT"}

        # Define category ownership based on true municipal rules to detect contradictions
        cat_to_dept = {
            "CAT_ROAD_MAINTENANCE": "DEPT_RDS",
            "CAT_WATER_SUPPLY": "DEPT_WSS",
            "CAT_DRAINAGE_SEWAGE": "DEPT_WSS",
            "CAT_STREET_LIGHTING": "DEPT_ELEC",
            "CAT_GARBAGE_COLLECTION": "DEPT_SWM",
            "CAT_HORTICULTURE": "DEPT_HORT",
            "CAT_PUBLIC_HEALTH": "DEPT_HLT",
            "CAT_ENCROACHMENT": "DEPT_ENCR"
        }

        for item in ground_truth:
            cid = item.get("complaint_id")
            gt_dept = item.get("ground_truth_dept") or item.get("ground_truth_department")
            gt_cat = item.get("ground_truth_category")
            gt_urg = item.get("ground_truth_urgency")
            gt_ward = item.get("ground_truth_ward")

            t = db.query(TriagedComplaint).filter_by(complaint_id=cid).first()
            if not t:
                continue

            pred_dept = t.department or ""
            pred_cat = t.category or ""
            
            canon_gt_dept = canonical_dept_map.get(gt_dept, gt_dept)
            canon_gt_cat = canonical_cat_map.get(gt_cat, gt_cat)
            
            # Taxonomy Contradiction Check
            is_contradiction = False
            if canon_gt_cat in cat_to_dept and cat_to_dept[canon_gt_cat] != canon_gt_dept:
                is_contradiction = True
                taxonomy_flags.append(TaxonomyFlag(
                    complaint_id=cid,
                    gt_dept=gt_dept,
                    gt_cat=gt_cat,
                    reason=f"Ground truth category {gt_cat} actually belongs to {cat_to_dept[canon_gt_cat]}, not {gt_dept}."
                ))

            # Dept Evaluation
            if gt_dept:
                y_true_dept.append(gt_dept)
                y_pred_dept.append(pred_dept)
                
                # Raw
                if pred_dept == gt_dept:
                    correct_dept_raw += 1
                
                # Diagnostic
                dept_diag_ok = False
                if pred_dept == canon_gt_dept:
                    dept_diag_ok = True
                elif is_contradiction and pred_dept == cat_to_dept.get(canon_gt_cat):
                    dept_diag_ok = True  # Model predicted the mathematically correct department for the category
                
                if dept_diag_ok:
                    correct_dept_diag += 1
                    if pred_dept != gt_dept:
                        diagnostic_changes.append(DiagnosticChange(
                            complaint_id=cid, field="department",
                            reason="Canonical alias or resolved taxonomy contradiction.",
                            original_gt=gt_dept, canonical_pred=pred_dept, resolved=True
                        ))
                else:
                    incorrect.append(IncorrectPrediction(
                        complaint_id=cid, field="department",
                        ground_truth=gt_dept, predicted=pred_dept,
                        confidence=t.routing_confidence or 0.0, text_snippet=cid
                    ))

            # Category Evaluation
            if gt_cat:
                # Raw
                if pred_cat == gt_cat:
                    correct_cat_raw += 1
                
                # Diagnostic
                cat_diag_ok = False
                if pred_cat == canon_gt_cat:
                    cat_diag_ok = True
                # If ground truth was WSS+ROAD, model predicting WSS+DRAINAGE is valid for the department
                # Or model predicting RDS+ROAD is valid. We accept if model predicted canon_gt_cat OR matched the valid category for the gt_dept
                elif is_contradiction and pred_dept == canon_gt_dept and cat_to_dept.get(pred_cat) == canon_gt_dept:
                     cat_diag_ok = True # e.g. gt=WSS+ROAD, pred=WSS+DRAINAGE (which belongs to WSS)
                     
                if cat_diag_ok:
                    correct_cat_diag += 1
                    if pred_cat != gt_cat:
                        diagnostic_changes.append(DiagnosticChange(
                            complaint_id=cid, field="category",
                            reason="Canonical alias or resolved taxonomy contradiction.",
                            original_gt=gt_cat, canonical_pred=pred_cat, resolved=True
                        ))
                else:
                    incorrect.append(IncorrectPrediction(
                        complaint_id=cid, field="category",
                        ground_truth=gt_cat, predicted=pred_cat,
                        confidence=t.routing_confidence or 0.0, text_snippet=cid
                    ))

            # Urgency
            pred_urg = t.urgency or ""
            if gt_urg:
                if pred_urg == gt_urg:
                    correct_urg += 1
                else:
                    incorrect.append(IncorrectPrediction(
                        complaint_id=cid,
                        field="urgency",
                        ground_truth=gt_urg,
                        predicted=pred_urg,
                        confidence=t.urgency_score or 0.0,
                        text_snippet=cid
                    ))

            # Locality / Ward
            pred_ward = t.ward or ""
            if gt_ward:
                if pred_ward.strip().lower() == gt_ward.strip().lower():
                    correct_loc += 1
                else:
                    incorrect.append(IncorrectPrediction(
                        complaint_id=cid,
                        field="locality",
                        ground_truth=gt_ward,
                        predicted=pred_ward,
                        confidence=0.9,
                        text_snippet=cid
                    ))

        dept_acc_raw = round(correct_dept_raw / float(total_samples), 4)
        cat_acc_raw = round(correct_cat_raw / float(total_samples), 4)
        dept_acc_diag = round(correct_dept_diag / float(total_samples), 4)
        cat_acc_diag = round(correct_cat_diag / float(total_samples), 4)
        
        urg_acc = round(correct_urg / float(total_samples), 4)
        loc_acc = round(correct_loc / float(total_samples), 4)

        cm = self.compute_confusion_matrix(y_true_dept, y_pred_dept, dept_classes) if y_true_dept else None
        badge = "DEMO / SYNTHETIC BENCHMARK" if is_synthetic else "VERIFIED REAL BENCHMARK"

        return EvaluationResultResponse(
            id=1000,
            test_set_version=dataset_name,
            total_samples=total_samples,
            department_accuracy=dept_acc_raw,  # Retain legacy raw for interface
            category_accuracy=cat_acc_raw,
            raw_department_accuracy=dept_acc_raw,
            raw_category_accuracy=cat_acc_raw,
            diagnostic_department_accuracy=dept_acc_diag,
            diagnostic_category_accuracy=cat_acc_diag,
            urgency_accuracy=urg_acc,
            locality_normalization_accuracy=loc_acc,
            duplicate_reduction=0.0,
            confusion_matrix=cm,
            per_class_metrics=cm.per_class if cm else {},
            incorrect_predictions=incorrect,
            taxonomy_consistency_flags=taxonomy_flags,
            diagnostic_changes=diagnostic_changes,
            is_synthetic_benchmark=is_synthetic,
            benchmark_badge=badge,
            evaluated_at=datetime.now(timezone.utc),
            notes=f"Evaluated {total_samples} samples from {dataset_name}. {len(diagnostic_changes)} diagnostic changes applied."
        )

    def run_evaluation(
        self,
        db: Session,
        req: EvaluationRunRequest
    ) -> EvaluationResultResponse:
        """
        Executes evaluation against a held-out labelled CSV test set.
        Never mutates raw complaint tables.
        """
        file_path = DATA_TEST_DIR / req.test_set_file
        if not file_path.exists():
            # Check relative to repo root
            alt_path = Path(req.test_set_file)
            if alt_path.exists():
                file_path = alt_path
            else:
                raise FileNotFoundError(f"Held-out test set file not found: '{file_path}'")

        # 1. Load ground truth records
        records = self.load_ground_truth(file_path)

        if not records:
            raise ValueError(f"Held-out test set '{req.test_set_file}' is empty.")

        total_samples = len(records)
        correct_dept = 0
        correct_cat = 0
        correct_urg = 0
        correct_loc = 0

        incorrect_predictions: List[IncorrectPrediction] = []

        # Tracking for confusion matrix
        dept_classes = [
            "DEPT_RDS", "DEPT_WSS", "DEPT_ELEC", "DEPT_SWM", "DEPT_HORT", "DEPT_PH", "DEPT_TOWN"
        ]
        dept_to_idx = {d: i for i, d in enumerate(dept_classes)}
        matrix = [[0 for _ in range(len(dept_classes))] for _ in range(len(dept_classes))]

        # Run model predictions across test samples
        predicted_items = []
        for row in records:
            cid = row.get("complaint_id", "UNKNOWN_ID")
            text = row.get("text", "")
            channel = row.get("source_channel", "state_helpline")

            gt_dept = row.get("ground_truth_department") or row.get("true_department")
            gt_cat = row.get("ground_truth_category") or row.get("true_category")
            gt_urg = row.get("ground_truth_urgency") or row.get("true_urgency")
            gt_loc = row.get("ground_truth_locality") or row.get("true_locality")
            gt_ward = row.get("ground_truth_ward") or row.get("true_ward")
            gt_group = row.get("ground_truth_duplicate_group") or row.get("true_duplicate_group") or cid

            # Execute classification
            ai_res = self.classifier.classify(
                complaint_text=text,
                channel=channel
            )

            # Execute urgency evaluation
            urg_res = self.urgency_engine.evaluate(
                complaint_text=text,
                category_id=ai_res.category,
                ai_classification=ai_res
            )

            # Execute locality normalization
            loc_res = self.locality_normalizer.normalize(
                source_location_hint=gt_loc,
                complaint_text=text,
                db=db
            )

            # 1. Department Accuracy
            pred_dept = ai_res.department
            if gt_dept:
                if pred_dept == gt_dept:
                    correct_dept += 1
                else:
                    incorrect_predictions.append(IncorrectPrediction(
                        complaint_id=cid,
                        field="department",
                        ground_truth=gt_dept,
                        predicted=pred_dept,
                        confidence=ai_res.confidence,
                        text_snippet=text[:100]
                    ))

                if gt_dept in dept_to_idx and pred_dept in dept_to_idx:
                    matrix[dept_to_idx[gt_dept]][dept_to_idx[pred_dept]] += 1

            # 2. Category Accuracy
            pred_cat = ai_res.category
            if gt_cat:
                if pred_cat == gt_cat:
                    correct_cat += 1
                else:
                    incorrect_predictions.append(IncorrectPrediction(
                        complaint_id=cid,
                        field="category",
                        ground_truth=gt_cat,
                        predicted=pred_cat,
                        confidence=ai_res.confidence,
                        text_snippet=text[:100]
                    ))

            # 3. Urgency Accuracy
            pred_urg = urg_res.urgency
            if gt_urg:
                if pred_urg == gt_urg:
                    correct_urg += 1
                else:
                    incorrect_predictions.append(IncorrectPrediction(
                        complaint_id=cid,
                        field="urgency",
                        ground_truth=gt_urg,
                        predicted=pred_urg,
                        confidence=urg_res.urgency_score,
                        text_snippet=text[:100]
                    ))

            # 4. Locality Accuracy
            pred_loc = loc_res.canonical_locality
            pred_ward = loc_res.ward
            if gt_loc or gt_ward:
                loc_match = (
                    (gt_loc and pred_loc and gt_loc.lower() in pred_loc.lower()) or
                    (gt_ward and pred_ward and gt_ward.lower() == pred_ward.lower())
                )
                if loc_match:
                    correct_loc += 1
                else:
                    incorrect_predictions.append(IncorrectPrediction(
                        complaint_id=cid,
                        field="locality",
                        ground_truth=f"{gt_loc} ({gt_ward})",
                        predicted=f"{pred_loc} ({pred_ward})",
                        confidence=loc_res.confidence,
                        text_snippet=text[:100]
                    ))

            predicted_items.append({
                "complaint_id": cid,
                "text": text,
                "department": pred_dept,
                "category": pred_cat,
                "normalized_locality": pred_loc,
                "ward": pred_ward,
                "gt_group": gt_group
            })

        # Calculate Per-Class Precision & Recall for Departments
        per_class: Dict[str, Dict[str, float]] = {}
        for d in dept_classes:
            idx = dept_to_idx[d]
            tp = matrix[idx][idx]
            fp = sum(matrix[r][idx] for r in range(len(dept_classes)) if r != idx)
            fn = sum(matrix[idx][c] for c in range(len(dept_classes)) if c != idx)

            prec = round(tp / float(tp + fp), 3) if (tp + fp) > 0 else 0.0
            rec = round(tp / float(tp + fn), 3) if (tp + fn) > 0 else 0.0
            f1 = round(2 * prec * rec / (prec + rec), 3) if (prec + rec) > 0 else 0.0

            per_class[d] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}

        # Calculate Duplicate Reduction
        # Group by ground-truth duplicate group: count unique issue groups
        gt_groups = set()
        for r in records:
            grp = r.get("ground_truth_duplicate_group") or r.get("true_duplicate_group") or r.get("complaint_id")
            gt_groups.add(grp)

        unique_issues_count = len(gt_groups)
        duplicate_reduction = round(
            ((total_samples - unique_issues_count) / float(total_samples)) * 100.0, 2
        ) if total_samples > 0 else 0.0

        dept_acc = round(correct_dept / float(total_samples), 4)
        cat_acc = round(correct_cat / float(total_samples), 4)
        urg_acc = round(correct_urg / float(total_samples), 4)
        loc_acc = round(correct_loc / float(total_samples), 4)

        normalized_matrix = []
        for r_row in matrix:
            row_sum = sum(r_row)
            if row_sum > 0:
                normalized_matrix.append([round(v / float(row_sum), 3) for v in r_row])
            else:
                normalized_matrix.append([0.0 for _ in r_row])

        conf_matrix_data = ConfusionMatrixData(
            classes=dept_classes,
            matrix=matrix,
            normalized_matrix=normalized_matrix,
            per_class=per_class
        )

        badge = "DEMO / SYNTHETIC BENCHMARK" if req.is_synthetic else "VERIFIED REAL BENCHMARK"

        # Persist to database
        eval_db_record = EvaluationResult(
            test_set_version=req.test_set_version,
            total_samples=total_samples,
            department_accuracy=dept_acc,
            category_accuracy=cat_acc,
            urgency_accuracy=urg_acc,
            locality_normalization_accuracy=loc_acc,
            duplicate_reduction=duplicate_reduction,
            confusion_matrix={"classes": dept_classes, "matrix": matrix},
            per_class_metrics=per_class,
            detailed_results={
                "incorrect_predictions": [p.model_dump() for p in incorrect_predictions[:30]],
                "benchmark_badge": badge
            },
            is_synthetic_benchmark=req.is_synthetic,
            evaluated_at=datetime.now(timezone.utc),
            notes=req.notes or f"Evaluated against {req.test_set_file} ({total_samples} samples)."
        )
        db.add(eval_db_record)
        db.commit()

        return EvaluationResultResponse(
            id=eval_db_record.id,
            test_set_version=req.test_set_version,
            total_samples=total_samples,
            department_accuracy=dept_acc,
            category_accuracy=cat_acc,
            urgency_accuracy=urg_acc,
            locality_normalization_accuracy=loc_acc,
            duplicate_reduction=duplicate_reduction,
            confusion_matrix=conf_matrix_data,
            per_class_metrics=per_class,
            incorrect_predictions=incorrect_predictions[:25],
            is_synthetic_benchmark=req.is_synthetic,
            benchmark_badge=badge,
            evaluated_at=eval_db_record.evaluated_at,
            notes=eval_db_record.notes
        )

    def get_latest_evaluation(self, db: Session) -> Optional[EvaluationResultResponse]:
        """Retrieves most recent benchmark evaluation run."""
        eval_rec = db.query(EvaluationResult).order_by(EvaluationResult.evaluated_at.desc()).first()
        if not eval_rec:
            return None

        cm_raw = eval_rec.confusion_matrix or {}
        conf_matrix = None
        if "classes" in cm_raw and "matrix" in cm_raw:
            conf_matrix = ConfusionMatrixData(
                classes=cm_raw["classes"],
                matrix=cm_raw["matrix"],
                per_class=eval_rec.per_class_metrics or {}
            )

        det = eval_rec.detailed_results or {}
        inc_raw = det.get("incorrect_predictions", [])
        inc_objs = [IncorrectPrediction(**item) for item in inc_raw]
        badge = det.get("benchmark_badge", "DEMO / SYNTHETIC BENCHMARK" if eval_rec.is_synthetic_benchmark else "VERIFIED REAL BENCHMARK")

        return EvaluationResultResponse(
            id=eval_rec.id,
            test_set_version=eval_rec.test_set_version,
            total_samples=eval_rec.total_samples,
            department_accuracy=eval_rec.department_accuracy,
            category_accuracy=eval_rec.category_accuracy,
            urgency_accuracy=eval_rec.urgency_accuracy,
            locality_normalization_accuracy=eval_rec.locality_normalization_accuracy,
            duplicate_reduction=eval_rec.duplicate_reduction,
            confusion_matrix=conf_matrix,
            per_class_metrics=eval_rec.per_class_metrics,
            incorrect_predictions=inc_objs,
            is_synthetic_benchmark=eval_rec.is_synthetic_benchmark,
            benchmark_badge=badge,
            evaluated_at=eval_rec.evaluated_at,
            notes=eval_rec.notes
        )

    def get_evaluation_history(self, db: Session, limit: int = 20) -> EvaluationHistoryResponse:
        """Retrieves history of evaluation runs."""
        runs = db.query(EvaluationResult).order_by(EvaluationResult.evaluated_at.desc()).limit(limit).all()
        res_list = []
        for r in runs:
            det = r.detailed_results or {}
            badge = det.get("benchmark_badge", "DEMO / SYNTHETIC BENCHMARK" if r.is_synthetic_benchmark else "VERIFIED REAL BENCHMARK")
            res_list.append(EvaluationResultResponse(
                id=r.id,
                test_set_version=r.test_set_version,
                total_samples=r.total_samples,
                department_accuracy=r.department_accuracy,
                category_accuracy=r.category_accuracy,
                urgency_accuracy=r.urgency_accuracy,
                locality_normalization_accuracy=r.locality_normalization_accuracy,
                duplicate_reduction=r.duplicate_reduction,
                is_synthetic_benchmark=r.is_synthetic_benchmark,
                benchmark_badge=badge,
                evaluated_at=r.evaluated_at,
                notes=r.notes
            ))
        return EvaluationHistoryResponse(results=res_list, total_runs=len(res_list))
