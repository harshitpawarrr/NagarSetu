"""
Triage Schemas for NagarSetu
Defines structured data contracts for AI classification, deterministic urgency scoring,
locality normalization, explainable routing, and operator review inspection.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.complaint import UrgencyLevel, ProcessingStatus


class AIClassificationResult(BaseModel):
    """Structured response from the AI Classification Service."""
    language: str = Field(..., description="Detected language code (e.g. en, hi, hi-Latn)")
    summary: str = Field(..., description="Concise operator-facing summary of the grievance")
    department: str = Field(..., description="Predicted municipal department ID (e.g. DEPT_ELEC)")
    category: str = Field(..., description="Predicted category ID (e.g. CAT_STREET_LIGHTING)")
    subcategory: Optional[str] = Field(default=None, description="Predicted subcategory or null if unmentioned")
    routing_terms: List[str] = Field(default_factory=list, description="Key extracted words justifying routing")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model classification confidence score (0.0 to 1.0)")


class UrgencyEvaluationResult(BaseModel):
    """Component scoring and safety override assessment for ticket urgency."""
    urgency: UrgencyLevel = Field(..., description="Final urgency level (CRITICAL, HIGH, MEDIUM, LOW)")
    urgency_score: float = Field(..., ge=0.0, le=1.0, description="Normalized urgency score from 0.0 to 1.0")
    safety_score: int = Field(..., ge=0, le=40, description="Public safety risk component (0-40)")
    outage_score: int = Field(..., ge=0, le=30, description="Service outage scale component (0-30)")
    duration_score: int = Field(..., ge=0, le=30, description="Reported problem duration component (0-30)")
    urgency_reason: str = Field(..., description="Human-readable justification for the score and urgency level")
    urgency_evidence: List[str] = Field(default_factory=list, description="Extracted terms or signals triggering scores")
    safety_override_applied: bool = Field(default=False, description="True if mandatory safety rule overrode AI score")
    safety_override_rule_id: Optional[str] = Field(default=None, description="Triggered safety override rule ID if applied")


class LocalityNormalizationResult(BaseModel):
    """Resolution of informal complaint text against the municipal gazetteer."""
    canonical_locality: str = Field(..., description="Standardized locality name or UNKNOWN")
    ward: Optional[str] = Field(default=None, description="Resolved municipal Ward ID/number")
    zone: Optional[str] = Field(default=None, description="Resolved administrative Zone name")
    match_type: str = Field(default="none", description="Match mechanism: exact_canonical, alias_match, landmark_match, none")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Gazetteer resolution confidence")


class ExplainableRoutingResult(BaseModel):
    """Explainable routing recommendation citing deterministic rules or charter clauses."""
    recommended_department: str = Field(..., description="Final routed department ID (e.g. DEPT_RDS)")
    routing_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in routing recommendation")
    routing_evidence: List[str] = Field(default_factory=list, description="Keywords and category matches justifying route")
    routing_rule_id: str = Field(..., description="ID of the matching deterministic routing rule or AI fallback")
    routing_explanation: str = Field(..., description="Human-readable auditable routing justification")


class ReviewFlagsResult(BaseModel):
    """Operational triage review flags based on confidence thresholds and safety rules."""
    requires_manual_review: bool = Field(default=False, description="True if confidence is low or unknown mapping occurred")
    review_flagged: bool = Field(default=False, description="True if ticket warrants operator attention")
    review_reason: Optional[str] = Field(default=None, description="Reason why manual review or attention is required")
    confidence_tier: str = Field(default="NORMAL", description="Confidence tier: NORMAL, ATTENTION, MANUAL_REVIEW")


class TriageAuditMetadata(BaseModel):
    """Complete audit metadata container stored in triaged_complaints.triage_metadata."""
    classification: AIClassificationResult
    urgency_breakdown: UrgencyEvaluationResult
    locality: LocalityNormalizationResult
    routing: ExplainableRoutingResult
    review_flags: ReviewFlagsResult
    model_version: str
    prompt_version: str
    processed_at: datetime


class ComplaintTriageResponse(BaseModel):
    """Response payload returned by the triage process and retrieval endpoints."""
    complaint_id: str
    original_channel: str
    original_text: str
    processing_status: ProcessingStatus
    language: str
    summary: str
    department: str
    category: str
    subcategory: Optional[str] = None
    urgency: UrgencyLevel
    urgency_score: float
    urgency_reason: str
    normalized_locality: str
    ward: Optional[str] = None
    zone: Optional[str] = None
    routing_evidence: str
    routing_confidence: float
    acknowledgement_draft: str
    triage_audit: TriageAuditMetadata
    processed_at: datetime
