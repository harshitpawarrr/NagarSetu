"""
High-Level API Contracts and Request/Response Schemas for NagarSetu
Adheres to RESTful best practices with type-safe request bodies and paginated responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.complaint import (
    CanonicalComplaint,
    ComplaintChannel,
    UrgencyLevel,
    ProcessingStatus,
    MultimodalAttachment
)


class PaginationMeta(BaseModel):
    total_records: int
    page: int
    page_size: int
    total_pages: int


class ComplaintIngestItem(BaseModel):
    """Payload for importing an individual exported raw record."""
    source_reference_id: Optional[str] = None
    original_channel: ComplaintChannel
    raw_text: str
    reported_at: Optional[datetime] = None
    raw_locality_hint: Optional[str] = None
    attachments: List[MultimodalAttachment] = Field(default_factory=list)


class BatchIngestRequest(BaseModel):
    batch_source_name: str
    items: List[ComplaintIngestItem]


class BatchIngestResponse(BaseModel):
    batch_id: str
    total_submitted: int
    successfully_queued: int
    failed_count: int
    message: str


class RejectedRowDetail(BaseModel):
    row_index: int
    complaint_id: Optional[str] = None
    reason: str
    raw_snippet: Optional[str] = None


class BatchIngestSummaryResponse(BaseModel):
    import_id: str
    file_name: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    duplicate_ids: List[str] = Field(default_factory=list)
    missing_content_rows: List[int] = Field(default_factory=list)
    text_only_rows: int = 0
    voice_rows: int = 0
    image_rows: int = 0
    multimodal_rows: int = 0
    warnings: List[str] = Field(default_factory=list)
    created_complaints_count: int = 0
    rejected_details: List[RejectedRowDetail] = Field(default_factory=list)
    message: str


class ComplaintFilterParams(BaseModel):
    department: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[UrgencyLevel] = None
    status: Optional[ProcessingStatus] = None
    ward: Optional[str] = None
    zone: Optional[str] = None
    search_query: Optional[str] = None
    cluster_id: Optional[str] = None
    page: int = 1
    page_size: int = 25


class PaginatedComplaintList(BaseModel):
    data: List[CanonicalComplaint]
    pagination: PaginationMeta


class OperatorReviewRequest(BaseModel):
    """Operator action payload: approving, editing draft, or overriding routing/urgency."""
    operator_id: str
    status: ProcessingStatus = ProcessingStatus.OPERATOR_APPROVED
    department_override: Optional[str] = None
    urgency_override: Optional[UrgencyLevel] = None
    ward_override: Optional[str] = None
    approved_acknowledgement: str
    operator_notes: Optional[str] = None


class ClusterDetailResponse(BaseModel):
    cluster_id: str
    summary: str
    department: str
    ward: Optional[str] = None
    complaints_count: int
    complaints: List[CanonicalComplaint]
    root_incident_id: Optional[str] = None


# Evaluation Data Contracts
class EvaluationMetricSummary(BaseModel):
    total_test_samples: int
    department_routing_accuracy: float = Field(..., ge=0.0, le=1.0)
    category_accuracy: float = Field(..., ge=0.0, le=1.0)
    urgency_agreement_score: float = Field(..., ge=0.0, le=1.0)
    locality_normalization_accuracy: float = Field(..., ge=0.0, le=1.0)
    duplicate_reduction_percentage: float = Field(..., ge=0.0, le=100.0)
    evaluation_run_at: datetime
    test_dataset_name: str
    disclaimer: str = "Evaluated against held-out labelled test dataset without fabricated results"


class EvaluationRunRequest(BaseModel):
    test_dataset_path: Optional[str] = None
    sample_limit: Optional[int] = None
