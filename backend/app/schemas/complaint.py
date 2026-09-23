"""
Canonical Complaint Schema for NagarSetu
Defines the core data models, enums, and structures for municipal complaint records.
All fields adhere strictly to the NagarSetu project specification.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ComplaintChannel(str, Enum):
    STATE_HELPLINE = "state_helpline"
    MUNICIPAL_APP = "municipal_app"
    ELECTED_REP_MESSAGE = "elected_rep_message"
    SOCIAL_MEDIA = "social_media"
    WALK_IN_PETITION = "walk_in_petition"


class UrgencyLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ProcessingStatus(str, Enum):
    RAW = "RAW"
    PREPROCESSED = "PREPROCESSED"
    CLASSIFIED = "CLASSIFIED"
    OPERATOR_REVIEW_PENDING = "OPERATOR_REVIEW_PENDING"
    OPERATOR_APPROVED = "OPERATOR_APPROVED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class InputModality(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE_CAPTION = "image_caption"


class MultimodalAttachment(BaseModel):
    """Stores metadata for voice notes, speech transcriptions, and photos with captions."""
    modality: InputModality
    file_uri: Optional[str] = None
    caption: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    transcription: Optional[str] = None
    extracted_ocr_text: Optional[str] = None


class OperatorReview(BaseModel):
    """Captures human operator review, approvals, and potential overrides."""
    operator_id: str
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    department_override: Optional[str] = None
    urgency_override: Optional[UrgencyLevel] = None
    ward_override: Optional[str] = None
    approved_acknowledgement: Optional[str] = None
    operator_notes: Optional[str] = None
    is_approved: bool = True


class CanonicalComplaint(BaseModel):
    """
    Canonical internal representation of a municipal complaint ticket.
    Every processed complaint within NagarSetu conforms to this schema.
    """
    model_config = ConfigDict(frozen=False, populate_by_name=True)

    # Core Identifiers & Source Details
    complaint_id: str = Field(..., description="Unique deterministic or generated identifier for the ticket")
    original_channel: ComplaintChannel = Field(..., description="Source origin of the complaint")
    original_text: str = Field(..., description="Original raw unstructured complaint text / caption / transcription")
    language: str = Field(default="en", description="Detected ISO-639-1 language code (e.g. en, hi, mr)")

    # Synthesis & Classification
    summary: str = Field(..., description="Concise operator-facing summary of the grievance")
    department: str = Field(..., description="Assigned municipal department code (e.g. DEPT_SWM)")
    category: str = Field(..., description="Primary category identifier (e.g. CAT_GARBAGE_COLLECTION)")
    subcategory: Optional[str] = Field(default=None, description="Granular subcategory identifier")

    # Risk & Urgency Scoring
    urgency: UrgencyLevel = Field(..., description="Triage urgency rating (CRITICAL, HIGH, MEDIUM, LOW)")
    urgency_score: float = Field(..., ge=0.0, le=1.0, description="Normalized urgency score from 0.0 to 1.0")
    urgency_reason: str = Field(..., description="Explainable justification or deterministic safety rule trigger")

    # Geographic & Locality Normalization
    normalized_locality: str = Field(..., description="Locality resolved against the municipal gazetteer")
    ward: Optional[str] = Field(default=None, description="Resolved municipal Ward ID or Number")
    zone: Optional[str] = Field(default=None, description="Resolved administrative Zone ID or Name")

    # Clustering & Duplicate Detection
    duplicate_cluster_id: Optional[str] = Field(default=None, description="Cluster identifier grouping duplicate complaints")
    duplicate_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence that complaint belongs to cluster")

    # Explainability & Operator Transparency
    routing_evidence: str = Field(..., description="Auditable reasoning citing matched keywords, charter clauses, or rule IDs")
    routing_confidence: float = Field(..., ge=0.0, le=1.0, description="Model or heuristic confidence in the routing decision")

    # Human-in-the-Loop & Operations
    acknowledgement_draft: str = Field(..., description="Draft acknowledgement message requiring operator approval prior to dispatch")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when complaint entered system")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.OPERATOR_REVIEW_PENDING, description="Current workflow state")

    # Optional Multimodal & Operator Extensions
    attachments: List[MultimodalAttachment] = Field(default_factory=list, description="Audio, image, or transcript attachments")
    operator_review: Optional[OperatorReview] = Field(default=None, description="Audit record of human operator review")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible bag for pipeline debugging/timestamps")
