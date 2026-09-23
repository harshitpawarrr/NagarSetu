"""
Pydantic Schemas for NagarSetu Held-Out Test Set Evaluation.
Defines contracts for evaluation requests, multi-class performance metrics,
confusion matrices, and error inspection.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    """Request payload to execute evaluation against a held-out labelled test set."""
    test_set_file: str = Field("benchmark_held_out_30.csv", description="Filename in data/test/ directory")
    test_set_version: str = Field("v1.0-synthetic", description="Version identifier of benchmark set")
    is_synthetic: bool = Field(True, description="Flag indicating if benchmark dataset is synthetic/demo")
    notes: Optional[str] = None


class ConfusionMatrixData(BaseModel):
    """Confusion matrix representation for departmental routing."""
    classes: List[str]
    matrix: List[List[int]]
    normalized_matrix: Optional[List[List[float]]] = None
    per_class: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class IncorrectPrediction(BaseModel):
    """Detailed record of an individual misclassification for operator auditing."""
    complaint_id: str
    field: str
    ground_truth: str
    predicted: str
    confidence: Optional[float] = None
    text_snippet: Optional[str] = None


class DiagnosticChange(BaseModel):
    complaint_id: str
    field: str
    reason: str
    original_gt: str
    canonical_pred: str
    resolved: bool

class TaxonomyFlag(BaseModel):
    complaint_id: str
    gt_dept: str
    gt_cat: str
    reason: str

class EvaluationResultResponse(BaseModel):
    """Comprehensive benchmark evaluation scorecard."""
    id: Optional[int] = None
    test_set_version: str
    total_samples: int
    
    # Raw metrics
    department_accuracy: float
    category_accuracy: float
    raw_department_accuracy: Optional[float] = None
    raw_category_accuracy: Optional[float] = None
    
    # Diagnostic metrics
    diagnostic_department_accuracy: Optional[float] = None
    diagnostic_category_accuracy: Optional[float] = None
    
    urgency_accuracy: float
    locality_normalization_accuracy: float
    duplicate_reduction: float
    
    confusion_matrix: Optional[ConfusionMatrixData] = None
    per_class_metrics: Optional[Dict[str, Any]] = None
    incorrect_predictions: List[IncorrectPrediction] = Field(default_factory=list)
    
    # Diagnostic audit trail
    taxonomy_consistency_flags: List[TaxonomyFlag] = Field(default_factory=list)
    diagnostic_changes: List[DiagnosticChange] = Field(default_factory=list)
    
    is_synthetic_benchmark: bool
    benchmark_badge: str = "DEMO / SYNTHETIC BENCHMARK"
    evaluated_at: datetime
    notes: Optional[str] = None
    disclaimer: str = "[PROTOTYPE_ASSUMPTION] Metrics computed strictly against held-out labelled records. Not an official municipal accuracy claim."

class EvaluationHistoryResponse(BaseModel):
    """Historical record of evaluation benchmark runs."""
    results: List[EvaluationResultResponse]
    total_runs: int
