"""
Operator Audit Trail Relational Model for NagarSetu.
Tracks operator triage actions, field overrides, and approvals separately from AI recommendations.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class ComplaintAudit(Base):
    """
    Granular audit entry recording human operator actions and field overrides.
    Stores operator identity, timestamp, original value, new value, field changed, and rationale.
    """
    __tablename__ = "complaint_audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(
        String(64),
        ForeignKey("raw_complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    operator_id = Column(String(128), nullable=False, index=True)
    field_changed = Column(String(64), nullable=False)  # 'department', 'category', 'urgency', 'normalized_locality', 'ward', 'summary', 'status', 'cluster_membership', 'acknowledgement'
    original_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    raw_complaint = relationship("RawComplaint", back_populates="audit_entries")

    def __repr__(self) -> str:
        return f"<ComplaintAudit(complaint='{self.complaint_id}', field='{self.field_changed}', op='{self.operator_id}')>"
