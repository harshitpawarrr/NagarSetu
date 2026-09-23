"""
Pydantic Schemas for NagarSetu Duplicate & Incident Clustering.
Defines contracts for cluster summaries, member relationships, detection requests,
and ticket count reduction analytics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ClusterMemberDetail(BaseModel):
    """Details of a complaint member within an incident cluster."""
    complaint_id: str
    similarity_score: Optional[float] = None
    relationship_type: str = "LIKELY_DUPLICATE"
    matching_signals: Optional[Dict[str, Any]] = None
    is_confirmed: bool = True
    notes: Optional[str] = None
    added_at: datetime
    channel: Optional[str] = None
    text_snippet: Optional[str] = None
    summary: Optional[str] = None
    urgency: Optional[str] = None
    canonical_locality: Optional[str] = None
    ward: Optional[str] = None


class ClusterSummary(BaseModel):
    """Summary overview of an incident cluster."""
    cluster_id: str
    representative_summary: str
    category: Optional[str] = None
    department: Optional[str] = None
    canonical_locality: Optional[str] = None
    ward: Optional[str] = None
    complaint_count: int = 0
    channels: List[str] = Field(default_factory=list)
    first_reported_at: Optional[datetime] = None
    latest_reported_at: Optional[datetime] = None
    confidence: float
    is_active: bool = True
    created_at: datetime


class ClusterDetailResponse(ClusterSummary):
    """Detailed cluster view including member complaints and operator notes."""
    members: List[ClusterMemberDetail] = Field(default_factory=list)
    operator_notes: Optional[str] = None


class ClusterAnalytics(BaseModel):
    """Ticket reduction analytics derived from clustering."""
    raw_complaint_count: int
    unique_cluster_count: int
    unclustered_complaint_count: int
    unique_issue_count: int
    duplicate_or_related_count: int
    ticket_reduction_percentage: float
    formula_explanation: str = "(raw_complaint_count - unique_issue_count) / raw_complaint_count * 100"
    disclaimer: str = "[PROTOTYPE_ASSUMPTION] Metric computed against currently processed batch; not an official municipal benchmark claim."


class ClusterListResponse(BaseModel):
    """Paginated list of clusters along with dataset-wide clustering analytics."""
    clusters: List[ClusterSummary]
    total_clusters: int
    analytics: ClusterAnalytics


class ClusterDetectionRequest(BaseModel):
    """Request payload to trigger cluster detection."""
    recluster: bool = False
    threshold_duplicate: Optional[float] = None
    threshold_related: Optional[float] = None
    department: Optional[str] = None
    ward: Optional[str] = None


class ClusterDetectionResponse(BaseModel):
    """Result of running cluster detection across complaints."""
    success: bool
    clusters_created: int
    total_complaints_clustered: int
    analytics: ClusterAnalytics


class ClusterReviewRequest(BaseModel):
    """Operator action performed on a cluster."""
    action: str = Field(..., description="Action to perform: 'confirm', 'remove_member', or 'add_notes'")
    complaint_id: Optional[str] = Field(None, description="Complaint ID if removing or modifying a member")
    notes: Optional[str] = None
    operator_id: str = Field(..., description="ID of the municipal desk operator")


class ClusterReviewResponse(BaseModel):
    """Response confirming operator action on a cluster."""
    success: bool
    cluster_id: str
    action_taken: str
    message: str
    updated_cluster: Optional[ClusterSummary] = None
