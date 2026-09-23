"""
Acknowledgement Relational Model for NagarSetu.
Stores AI-drafted acknowledgements for human operator review and approval.

CRITICAL SCOPE CONSTRAINT:
In adherence to Rule 2.3 and Section 8 of the project specification, this model
STRICTLY PROHIBITS any external delivery, dispatch, or send connector fields.
Supported statuses are exclusively: 'draft', 'edited', 'approved'.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Acknowledgement(Base):
    """
    Operator-governed citizen acknowledgement draft.
    Requires explicit human approval prior to being finalized.
    """
    __tablename__ = "acknowledgements"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'edited', 'approved')", name="chk_acknowledgement_status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(
        String(64),
        ForeignKey("raw_complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    draft_text = Column(Text, nullable=False)
    language = Column(String(16), default="en", nullable=False)
    status = Column(String(32), default="draft", nullable=False, index=True)  # draft, edited, approved
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(128), nullable=True)  # Operator ID who signed off

    # Relationships
    raw_complaint = relationship("RawComplaint", back_populates="acknowledgements")

    def __repr__(self) -> str:
        return f"<Acknowledgement(id={self.id}, complaint='{self.complaint_id}', status='{self.status}')>"
