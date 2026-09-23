"""
Complaint Relational Models for NagarSetu.
Enforces strict immutability of raw records and separates triaged/derived outputs.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, ForeignKey, event, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class ImmutableDataError(Exception):
    """Raised when an attempt is made to modify or delete immutable raw audit data."""
    pass


class RawComplaint(Base):
    """
    Represents the original exported complaint dataset.
    STRICTLY IMMUTABLE: Records cannot be updated or deleted once inserted.
    Original inputs remain fully auditable.
    """
    __tablename__ = "raw_complaints"

    complaint_id = Column(String(64), primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    channel = Column(String(64), nullable=True, index=True)  # e.g., state_helpline, municipal_app, social_media
    text = Column(Text, nullable=True)
    audio_path = Column(String(512), nullable=True)
    image_path = Column(String(512), nullable=True)
    image_caption = Column(Text, nullable=True)
    source_location = Column(String(256), nullable=True)
    department_label = Column(String(64), nullable=True)  # Optional raw source tag
    category_label = Column(String(64), nullable=True)    # Optional raw source tag
    urgency_label = Column(String(32), nullable=True)     # Optional raw source tag
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    triaged_record = relationship("TriagedComplaint", back_populates="raw_complaint", uselist=False, passive_deletes=True)
    status_history_entries = relationship("StatusHistory", back_populates="raw_complaint", passive_deletes=True)
    cluster_memberships = relationship("ClusterMember", back_populates="raw_complaint", passive_deletes=True)
    acknowledgements = relationship("Acknowledgement", back_populates="raw_complaint", passive_deletes=True)
    audit_entries = relationship("ComplaintAudit", back_populates="raw_complaint", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<RawComplaint(id='{self.complaint_id}', channel='{self.channel}')>"


# ORM Immutability Protection Hooks
@event.listens_for(RawComplaint, "before_update")
def prevent_raw_complaint_update(mapper, connection, target):
    raise ImmutableDataError(
        f"Raw complaint record '{target.complaint_id}' is immutable and cannot be updated. "
        f"Store processed outputs in triaged_complaints instead."
    )


@event.listens_for(RawComplaint, "before_delete")
def prevent_raw_complaint_delete(mapper, connection, target):
    raise ImmutableDataError(
        f"Raw complaint record '{target.complaint_id}' is immutable and cannot be deleted."
    )


from sqlalchemy.orm import Session as SASession


@event.listens_for(SASession, "before_flush")
def validate_immutability_on_flush(session, flush_context, instances):
    for obj in session.dirty:
        if isinstance(obj, RawComplaint) and session.is_modified(obj):
            raise ImmutableDataError(
                f"Raw complaint record '{obj.complaint_id}' is immutable and cannot be updated. "
                f"Store processed outputs in triaged_complaints instead."
            )
    for obj in session.deleted:
        if isinstance(obj, RawComplaint):
            raise ImmutableDataError(
                f"Raw complaint record '{obj.complaint_id}' is immutable and cannot be deleted."
            )


class TriagedComplaint(Base):
    """
    Stores processed, enriched, and classified complaint data.
    Derived by AI classification and deterministic business rules.
    Does not assume all values are present prior to processing.
    """
    __tablename__ = "triaged_complaints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(
        String(64),
        ForeignKey("raw_complaints.complaint_id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True
    )
    language = Column(String(16), nullable=True)
    summary = Column(Text, nullable=True)
    department = Column(String(64), ForeignKey("departments.department_id", ondelete="SET NULL"), nullable=True, index=True)
    category = Column(String(64), ForeignKey("categories.category_id", ondelete="SET NULL"), nullable=True, index=True)
    subcategory = Column(String(128), nullable=True)
    urgency = Column(String(32), nullable=True, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    urgency_score = Column(Float, nullable=True)
    urgency_reason = Column(Text, nullable=True)
    normalized_locality = Column(String(256), nullable=True, index=True)
    ward = Column(String(64), nullable=True, index=True)
    zone = Column(String(64), nullable=True, index=True)
    duplicate_cluster_id = Column(String(64), ForeignKey("duplicate_clusters.cluster_id", ondelete="SET NULL"), nullable=True, index=True)
    duplicate_confidence = Column(Float, nullable=True)
    routing_evidence = Column(Text, nullable=True)
    routing_confidence = Column(Float, nullable=True)
    acknowledgement_id = Column(Integer, ForeignKey("acknowledgements.id", ondelete="SET NULL"), nullable=True)
    processing_status = Column(String(64), default="OPERATOR_REVIEW_PENDING", nullable=False, index=True)
    model_version = Column(String(64), nullable=True)
    prompt_version = Column(String(64), nullable=True)
    multimodal_payload = Column(JSON, nullable=True)  # Normalized multimodal representation
    triage_metadata = Column(JSON, nullable=True)     # Detailed triage scoring, safety override, and routing audit
    operator_overrides = Column(JSON, nullable=True)  # Detailed log of operator overrides for fields
    operator_decision = Column(JSON, nullable=True)   # Final operator decision payload
    resolved_at = Column(DateTime(timezone=True), nullable=True)  # When status reached RESOLVED
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    raw_complaint = relationship("RawComplaint", back_populates="triaged_record")
    department_rel = relationship("Department", back_populates="triaged_complaints")
    category_rel = relationship("Category", back_populates="triaged_complaints")
    cluster_rel = relationship("DuplicateCluster", back_populates="triaged_complaints")
    acknowledgement_rel = relationship("Acknowledgement", foreign_keys=[acknowledgement_id])

    def __repr__(self) -> str:
        return f"<TriagedComplaint(complaint_id='{self.complaint_id}', dept='{self.department}', urgency='{self.urgency}')>"


class StatusHistory(Base):
    """
    Audit trail tracking complaint status changes and operator reviews.
    """
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(
        String(64),
        ForeignKey("raw_complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    old_status = Column(String(64), nullable=True)
    new_status = Column(String(64), nullable=False, index=True)
    changed_by = Column(String(128), nullable=False)  # e.g., system_ingestion, operator_id
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    raw_complaint = relationship("RawComplaint", back_populates="status_history_entries")

    def __repr__(self) -> str:
        return f"<StatusHistory(complaint='{self.complaint_id}', {self.old_status} -> {self.new_status})>"
