"""
Duplicate Cluster and Cluster Membership Relational Models for NagarSetu.
Groups repeated or related civic complaints into auditable clusters while preserving
every individual original complaint record.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class DuplicateCluster(Base):
    """
    Represents an incident cluster grouping multiple duplicate or related complaints.
    """
    __tablename__ = "duplicate_clusters"

    cluster_id = Column(String(64), primary_key=True, index=True)
    summary = Column(Text, nullable=False)  # Representative or canonical issue summary
    confidence = Column(Float, nullable=False)  # Cluster cohesion confidence (0.0 to 1.0)
    detection_method = Column(String(64), nullable=False)  # e.g., 'multi_signal_weighted', 'operator_merged'
    category = Column(String(64), nullable=True, index=True)
    department = Column(String(64), nullable=True, index=True)
    canonical_locality = Column(String(256), nullable=True, index=True)
    ward = Column(String(64), nullable=True, index=True)
    first_reported_at = Column(DateTime(timezone=True), nullable=True)
    latest_reported_at = Column(DateTime(timezone=True), nullable=True)
    operator_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    members = relationship("ClusterMember", back_populates="cluster", cascade="all, delete-orphan")
    triaged_complaints = relationship("TriagedComplaint", back_populates="cluster_rel")

    def __repr__(self) -> str:
        return f"<DuplicateCluster(id='{self.cluster_id}', confidence={self.confidence}, dept='{self.department}')>"


class ClusterMember(Base):
    """
    Links individual complaint records to an incident cluster.
    Preserves audit linkage without altering the underlying raw complaint.
    """
    __tablename__ = "cluster_members"
    __table_args__ = (
        UniqueConstraint("cluster_id", "complaint_id", name="uq_cluster_complaint"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(64), ForeignKey("duplicate_clusters.cluster_id", ondelete="CASCADE"), nullable=False, index=True)
    complaint_id = Column(String(64), ForeignKey("raw_complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=True)
    relationship_type = Column(String(32), default="LIKELY_DUPLICATE", nullable=False)  # LIKELY_DUPLICATE, RELATED_INCIDENT, NO_MATCH
    matching_signals = Column(JSON, nullable=True)  # Signal weights & breakdown dictionary
    is_confirmed = Column(Boolean, default=True, nullable=False)  # Operator confirmation
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    cluster = relationship("DuplicateCluster", back_populates="members")
    raw_complaint = relationship("RawComplaint", back_populates="cluster_memberships")

    def __repr__(self) -> str:
        return f"<ClusterMember(cluster='{self.cluster_id}', complaint='{self.complaint_id}', type='{self.relationship_type}')>"
