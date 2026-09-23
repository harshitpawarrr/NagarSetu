"""
Operator Desk and Human-in-the-Loop Review Service for NagarSetu.
Manages operator triage approval, field overrides, audit logging, and acknowledgement sign-off.
Strictly preserves raw complaint immutability and isolates AI recommendations from operator decisions.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.models.audit import ComplaintAudit
from app.models.acknowledgement import Acknowledgement
from app.schemas.operator import (
    OperatorReviewRequest,
    OperatorReviewResponse,
    AuditEntryResponse,
    AcknowledgementEditRequest,
    AcknowledgementApproveRequest,
    AcknowledgementResponse
)

logger = logging.getLogger("nagarsetu.operator_service")

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "config"


class OperatorService:
    """
    Coordinates operator actions, overrides, audit history, and acknowledgement governance.
    """

    def __init__(self):
        # Cache valid departments and categories from config for validation
        self.valid_departments = set()
        self.valid_categories = set()
        dept_path = CONFIG_DIR / "departments.json"
        cat_path = CONFIG_DIR / "categories.json"

        if dept_path.exists():
            with open(dept_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.valid_departments = {d["department_id"] for d in data.get("departments", [])}

        if cat_path.exists():
            with open(cat_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.valid_categories = {c["category_id"] for c in data.get("categories", [])}

        self.valid_urgencies = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

    def review_complaint(
        self,
        db: Session,
        complaint_id: str,
        req: OperatorReviewRequest
    ) -> OperatorReviewResponse:
        """
        Executes operator triage review, approval, or overrides.
        Maintains AI recommendations in triage_metadata and persists operator decision separately.
        """
        tc = db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == complaint_id).first()
        if not tc:
            raise ValueError(f"Complaint '{complaint_id}' has not been triaged yet.")

        old_status = tc.processing_status
        audit_entries_created = []
        now_dt = datetime.now(timezone.utc)
        overrides_dict = tc.operator_overrides or {}

        if req.action == "approve":
            tc.processing_status = "OPERATOR_APPROVED"

            # Create status audit entry
            status_audit = ComplaintAudit(
                complaint_id=complaint_id,
                operator_id=req.operator_id,
                field_changed="processing_status",
                original_value=old_status,
                new_value="OPERATOR_APPROVED",
                reason=req.notes or "AI recommendations approved without overrides by operator",
                created_at=now_dt
            )
            db.add(status_audit)
            audit_entries_created.append(status_audit)

            # Add status history
            db.add(StatusHistory(
                complaint_id=complaint_id,
                old_status=old_status,
                new_status="OPERATOR_APPROVED",
                changed_by=req.operator_id,
                timestamp=now_dt,
                notes=req.notes or "Triage approved by operator"
            ))

            tc.operator_decision = {
                "approved_by": req.operator_id,
                "approved_at": now_dt.isoformat(),
                "status": "APPROVED",
                "notes": req.notes
            }

        elif req.action == "flag_manual_review":
            tc.processing_status = "MANUAL_REVIEW_FLAGGED"
            flag_audit = ComplaintAudit(
                complaint_id=complaint_id,
                operator_id=req.operator_id,
                field_changed="processing_status",
                original_value=old_status,
                new_value="MANUAL_REVIEW_FLAGGED",
                reason=req.reason or req.notes or "Flagged by operator for senior supervisory review",
                created_at=now_dt
            )
            db.add(flag_audit)
            audit_entries_created.append(flag_audit)

            db.add(StatusHistory(
                complaint_id=complaint_id,
                old_status=old_status,
                new_status="MANUAL_REVIEW_FLAGGED",
                changed_by=req.operator_id,
                timestamp=now_dt,
                notes=req.reason or "Flagged for manual review"
            ))

            tc.operator_decision = {
                "flagged_by": req.operator_id,
                "flagged_at": now_dt.isoformat(),
                "status": "MANUAL_REVIEW_FLAGGED",
                "reason": req.reason
            }

        elif req.action == "override":
            if not req.reason:
                raise ValueError("A clear reason is required when overriding AI triage fields.")

            fields_overridden = []

            # 1. Department Override
            if req.department and req.department != tc.department:
                if self.valid_departments and req.department not in self.valid_departments:
                    raise ValueError(f"Invalid department '{req.department}'. Valid options: {sorted(list(self.valid_departments))}")
                orig = tc.department
                tc.department = req.department
                audit = ComplaintAudit(
                    complaint_id=complaint_id,
                    operator_id=req.operator_id,
                    field_changed="department",
                    original_value=orig,
                    new_value=req.department,
                    reason=req.reason,
                    created_at=now_dt
                )
                db.add(audit)
                audit_entries_created.append(audit)
                overrides_dict["department"] = {
                    "original": orig,
                    "override": req.department,
                    "reason": req.reason,
                    "operator_id": req.operator_id,
                    "timestamp": now_dt.isoformat()
                }
                fields_overridden.append("department")

            # 2. Category Override
            if req.category and req.category != tc.category:
                if self.valid_categories and req.category not in self.valid_categories:
                    raise ValueError(f"Invalid category '{req.category}'. Valid options: {sorted(list(self.valid_categories))}")
                orig = tc.category
                tc.category = req.category
                audit = ComplaintAudit(
                    complaint_id=complaint_id,
                    operator_id=req.operator_id,
                    field_changed="category",
                    original_value=orig,
                    new_value=req.category,
                    reason=req.reason,
                    created_at=now_dt
                )
                db.add(audit)
                audit_entries_created.append(audit)
                overrides_dict["category"] = {
                    "original": orig,
                    "override": req.category,
                    "reason": req.reason,
                    "operator_id": req.operator_id,
                    "timestamp": now_dt.isoformat()
                }
                fields_overridden.append("category")

            # 3. Urgency Override
            if req.urgency and req.urgency != tc.urgency:
                if req.urgency not in self.valid_urgencies:
                    raise ValueError(f"Invalid urgency '{req.urgency}'. Valid options: {self.valid_urgencies}")
                orig = tc.urgency
                tc.urgency = req.urgency
                audit = ComplaintAudit(
                    complaint_id=complaint_id,
                    operator_id=req.operator_id,
                    field_changed="urgency",
                    original_value=orig,
                    new_value=req.urgency,
                    reason=req.reason,
                    created_at=now_dt
                )
                db.add(audit)
                audit_entries_created.append(audit)
                overrides_dict["urgency"] = {
                    "original": orig,
                    "override": req.urgency,
                    "reason": req.reason,
                    "operator_id": req.operator_id,
                    "timestamp": now_dt.isoformat()
                }
                fields_overridden.append("urgency")

            # 4. Normalized Locality & Ward Override
            if req.normalized_locality and req.normalized_locality != tc.normalized_locality:
                orig = tc.normalized_locality
                tc.normalized_locality = req.normalized_locality
                audit = ComplaintAudit(
                    complaint_id=complaint_id,
                    operator_id=req.operator_id,
                    field_changed="normalized_locality",
                    original_value=orig,
                    new_value=req.normalized_locality,
                    reason=req.reason,
                    created_at=now_dt
                )
                db.add(audit)
                audit_entries_created.append(audit)
                overrides_dict["normalized_locality"] = {
                    "original": orig,
                    "override": req.normalized_locality,
                    "reason": req.reason,
                    "operator_id": req.operator_id,
                    "timestamp": now_dt.isoformat()
                }
                fields_overridden.append("normalized_locality")

            if req.ward and req.ward != tc.ward:
                orig = tc.ward
                tc.ward = req.ward
                audit = ComplaintAudit(
                    complaint_id=complaint_id,
                    operator_id=req.operator_id,
                    field_changed="ward",
                    original_value=orig,
                    new_value=req.ward,
                    reason=req.reason,
                    created_at=now_dt
                )
                db.add(audit)
                audit_entries_created.append(audit)
                overrides_dict["ward"] = {
                    "original": orig,
                    "override": req.ward,
                    "reason": req.reason,
                    "operator_id": req.operator_id,
                    "timestamp": now_dt.isoformat()
                }
                fields_overridden.append("ward")

            # 5. Summary Override
            if req.summary and req.summary != tc.summary:
                orig = tc.summary
                tc.summary = req.summary
                audit = ComplaintAudit(
                    complaint_id=complaint_id,
                    operator_id=req.operator_id,
                    field_changed="summary",
                    original_value=orig,
                    new_value=req.summary,
                    reason=req.reason,
                    created_at=now_dt
                )
                db.add(audit)
                audit_entries_created.append(audit)
                overrides_dict["summary"] = {
                    "original": orig,
                    "override": req.summary,
                    "reason": req.reason,
                    "operator_id": req.operator_id,
                    "timestamp": now_dt.isoformat()
                }
                fields_overridden.append("summary")

            tc.operator_overrides = overrides_dict
            tc.processing_status = "OPERATOR_APPROVED"

            status_audit = ComplaintAudit(
                complaint_id=complaint_id,
                operator_id=req.operator_id,
                field_changed="processing_status",
                original_value=old_status,
                new_value="OPERATOR_APPROVED",
                reason=f"Approved with overrides to {', '.join(fields_overridden)}: {req.reason}",
                created_at=now_dt
            )
            db.add(status_audit)
            audit_entries_created.append(status_audit)

            db.add(StatusHistory(
                complaint_id=complaint_id,
                old_status=old_status,
                new_status="OPERATOR_APPROVED",
                changed_by=req.operator_id,
                timestamp=now_dt,
                notes=f"Approved with overrides: {req.reason}"
            ))

            tc.operator_decision = {
                "approved_by": req.operator_id,
                "approved_at": now_dt.isoformat(),
                "status": "APPROVED",
                "fields_overridden": fields_overridden,
                "reason": req.reason
            }

        else:
            raise ValueError(f"Unknown operator action: '{req.action}'")

        db.commit()

        # Build response audit items
        audit_res = [
            AuditEntryResponse(
                id=a.id or 0,
                complaint_id=a.complaint_id,
                operator_id=a.operator_id,
                field_changed=a.field_changed,
                original_value=a.original_value,
                new_value=a.new_value,
                reason=a.reason,
                created_at=a.created_at
            )
            for a in audit_entries_created
        ]

        return OperatorReviewResponse(
            success=True,
            complaint_id=complaint_id,
            processing_status=tc.processing_status,
            operator_decision=tc.operator_decision,
            audit_entries=audit_res,
            message=f"Complaint '{complaint_id}' updated with status '{tc.processing_status}'."
        )

    def get_audit_trail(self, db: Session, complaint_id: str) -> List[AuditEntryResponse]:
        """Returns complete chronological audit history of operator overrides and status transitions."""
        audits = db.query(ComplaintAudit).filter(
            ComplaintAudit.complaint_id == complaint_id
        ).order_by(ComplaintAudit.created_at.asc()).all()

        return [
            AuditEntryResponse(
                id=a.id,
                complaint_id=a.complaint_id,
                operator_id=a.operator_id,
                field_changed=a.field_changed,
                original_value=a.original_value,
                new_value=a.new_value,
                reason=a.reason,
                created_at=a.created_at
            )
            for a in audits
        ]

    def get_acknowledgement(self, db: Session, complaint_id: str) -> AcknowledgementResponse:
        """Retrieves current citizen acknowledgement draft."""
        ack = db.query(Acknowledgement).filter(Acknowledgement.complaint_id == complaint_id).first()
        if not ack:
            tc = db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == complaint_id).first()
            summary_snippet = tc.summary if tc else "Your complaint"
            ack = Acknowledgement(
                complaint_id=complaint_id,
                draft_text=f"Dear Citizen, your complaint regarding '{summary_snippet}' has been registered under ticket ID {complaint_id} and is assigned for departmental inspection.",
                language="en",
                status="draft",
                generated_at=datetime.now(timezone.utc)
            )
            db.add(ack)
            db.commit()

        return AcknowledgementResponse(
            id=ack.id,
            complaint_id=ack.complaint_id,
            draft_text=ack.draft_text,
            language=ack.language,
            status=ack.status,
            generated_at=ack.generated_at,
            edited_at=ack.edited_at,
            approved_at=ack.approved_at,
            approved_by=ack.approved_by
        )

    def edit_acknowledgement(
        self,
        db: Session,
        complaint_id: str,
        req: AcknowledgementEditRequest
    ) -> AcknowledgementResponse:
        """
        Allows operator to edit citizen draft acknowledgement.
        State transitions: 'draft' or 'edited' -> 'edited'.
        """
        ack = db.query(Acknowledgement).filter(Acknowledgement.complaint_id == complaint_id).first()
        now_dt = datetime.now(timezone.utc)

        if not ack:
            ack = Acknowledgement(
                complaint_id=complaint_id,
                draft_text=req.draft_text,
                language=req.language,
                status="edited",
                generated_at=now_dt,
                edited_at=now_dt
            )
            db.add(ack)
        else:
            orig = ack.draft_text
            ack.draft_text = req.draft_text
            ack.language = req.language
            ack.status = "edited"
            ack.edited_at = now_dt

            # Audit edit
            db.add(ComplaintAudit(
                complaint_id=complaint_id,
                operator_id=req.operator_id,
                field_changed="acknowledgement_text",
                original_value=orig,
                new_value=req.draft_text,
                reason="Operator edited draft acknowledgement text",
                created_at=now_dt
            ))

        db.commit()
        return AcknowledgementResponse(
            id=ack.id,
            complaint_id=ack.complaint_id,
            draft_text=ack.draft_text,
            language=ack.language,
            status=ack.status,
            generated_at=ack.generated_at,
            edited_at=ack.edited_at,
            approved_at=ack.approved_at,
            approved_by=ack.approved_by
        )

    def approve_acknowledgement(
        self,
        db: Session,
        complaint_id: str,
        req: AcknowledgementApproveRequest
    ) -> AcknowledgementResponse:
        """
        Operator signs off and approves citizen acknowledgement.
        Strictly internal state transition ('approved'); zero external network send.
        """
        ack = db.query(Acknowledgement).filter(Acknowledgement.complaint_id == complaint_id).first()
        now_dt = datetime.now(timezone.utc)

        if not ack:
            tc = db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == complaint_id).first()
            summary_snippet = tc.summary if tc else "Your complaint"
            ack = Acknowledgement(
                complaint_id=complaint_id,
                draft_text=f"Dear Citizen, your complaint regarding '{summary_snippet}' has been registered under ticket ID {complaint_id} and is assigned for departmental inspection.",
                language="en",
                status="approved",
                generated_at=now_dt,
                approved_at=now_dt,
                approved_by=req.operator_id
            )
            db.add(ack)
        else:
            orig_status = ack.status
            ack.status = "approved"
            ack.approved_at = now_dt
            ack.approved_by = req.operator_id

            # Audit approval
            db.add(ComplaintAudit(
                complaint_id=complaint_id,
                operator_id=req.operator_id,
                field_changed="acknowledgement_status",
                original_value=orig_status,
                new_value="approved",
                reason=req.notes or "Citizen acknowledgement approved by operator for internal records",
                created_at=now_dt
            ))

        db.commit()
        return AcknowledgementResponse(
            id=ack.id,
            complaint_id=ack.complaint_id,
            draft_text=ack.draft_text,
            language=ack.language,
            status=ack.status,
            generated_at=ack.generated_at,
            edited_at=ack.edited_at,
            approved_at=ack.approved_at,
            approved_by=ack.approved_by
        )
