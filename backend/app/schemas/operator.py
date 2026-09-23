"""
Pydantic Schemas for NagarSetu Operator Desk and Review Workflows.
Defines contracts for triage approval, granular overrides, audit trails,
and citizen acknowledgement sign-offs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuditEntryResponse(BaseModel):
    """Represents a single operator override or status change audit record."""
    id: int
    complaint_id: str
    operator_id: str
    field_changed: str
    original_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime


class OperatorReviewRequest(BaseModel):
    """Request payload for municipal operator triage review and overrides."""
    action: str = Field(..., description="'approve', 'override', or 'flag_manual_review'")
    department: Optional[str] = Field(None, description="Department ID override (e.g. 'DEPT_RDS')")
    category: Optional[str] = Field(None, description="Category ID override (e.g. 'CAT_ROAD_MAINTENANCE')")
    urgency: Optional[str] = Field(None, description="Urgency override ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')")
    normalized_locality: Optional[str] = Field(None, description="Normalized locality override")
    ward: Optional[str] = Field(None, description="Ward identifier override")
    summary: Optional[str] = Field(None, description="Edited operator summary")
    reason: Optional[str] = Field(None, description="Mandatory rationale for overrides")
    notes: Optional[str] = Field(None, description="Optional operator notes")
    operator_id: str = Field(..., description="Identifier of the operator performing review")


class OperatorReviewResponse(BaseModel):
    """Response returned upon operator review or override action."""
    success: bool
    complaint_id: str
    processing_status: str
    operator_decision: Optional[Dict[str, Any]] = None
    audit_entries: List[AuditEntryResponse] = Field(default_factory=list)
    message: str


class AcknowledgementEditRequest(BaseModel):
    """Payload for operator editing an acknowledgement draft."""
    draft_text: str = Field(..., min_length=5, description="Updated citizen acknowledgement text")
    language: str = Field("en", description="Language code")
    operator_id: str = Field(..., description="ID of the operator modifying the draft")


class AcknowledgementApproveRequest(BaseModel):
    """Payload for human operator sign-off on acknowledgement draft."""
    operator_id: str = Field(..., description="ID of the operator approving the draft")
    notes: Optional[str] = None


class AcknowledgementResponse(BaseModel):
    """Response returning citizen acknowledgement status."""
    id: int
    complaint_id: str
    draft_text: str
    language: str
    status: str  # 'draft', 'edited', 'approved'
    generated_at: datetime
    edited_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    disclaimer: str = "[NO_EXTERNAL_DISPATCH] In adherence to Rule 2.3, acknowledgement is strictly stored internally and never dispatched over network/SMS/email."
