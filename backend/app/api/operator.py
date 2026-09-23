"""
FastAPI Routes for NagarSetu Operator Desk, Triage Overrides, and Acknowledgements.
Provides endpoints for operator sign-off, granular field overrides, audit logs,
and human-in-the-loop acknowledgement approvals.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.operator import (
    OperatorReviewRequest,
    OperatorReviewResponse,
    AuditEntryResponse,
    AcknowledgementEditRequest,
    AcknowledgementApproveRequest,
    AcknowledgementResponse
)
from app.services.operator.operator_service import OperatorService

router = APIRouter(prefix="/complaints", tags=["Operator Desk & Reviews"])


def get_operator_service() -> OperatorService:
    return OperatorService()


@router.post("/{complaint_id}/review", response_model=OperatorReviewResponse)
def review_complaint(
    complaint_id: str,
    req: OperatorReviewRequest,
    db: Session = Depends(get_db),
    operator_service: OperatorService = Depends(get_operator_service)
):
    """
    Operator action on a complaint ticket:
    - 'approve': Approves AI recommendation
    - 'override': Applies granular department, category, urgency, locality, or summary overrides with required reason
    - 'flag_manual_review': Flags complaint for senior supervisory intervention
    All actions are audited. Original AI recommendations remain immutable.
    """
    try:
        return operator_service.review_complaint(db, complaint_id, req)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operator review failed: {str(e)}")


@router.get("/{complaint_id}/audit", response_model=List[AuditEntryResponse])
def get_complaint_audit_trail(
    complaint_id: str,
    db: Session = Depends(get_db),
    operator_service: OperatorService = Depends(get_operator_service)
):
    """
    Retrieves full chronological audit trail of operator reviews and overrides for a ticket.
    """
    return operator_service.get_audit_trail(db, complaint_id)


@router.get("/{complaint_id}/acknowledgement", response_model=AcknowledgementResponse)
def get_acknowledgement(
    complaint_id: str,
    db: Session = Depends(get_db),
    operator_service: OperatorService = Depends(get_operator_service)
):
    """
    Retrieves citizen acknowledgement draft for human operator review.
    """
    return operator_service.get_acknowledgement(db, complaint_id)


@router.put("/{complaint_id}/acknowledgement", response_model=AcknowledgementResponse)
def edit_acknowledgement(
    complaint_id: str,
    req: AcknowledgementEditRequest,
    db: Session = Depends(get_db),
    operator_service: OperatorService = Depends(get_operator_service)
):
    """
    Allows municipal operator to edit citizen draft text before sign-off.
    """
    try:
        return operator_service.edit_acknowledgement(db, complaint_id, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update acknowledgement: {str(e)}")


@router.post("/{complaint_id}/acknowledgement/approve", response_model=AcknowledgementResponse)
def approve_acknowledgement(
    complaint_id: str,
    req: AcknowledgementApproveRequest,
    db: Session = Depends(get_db),
    operator_service: OperatorService = Depends(get_operator_service)
):
    """
    Operator approves citizen acknowledgement draft.
    STRICT BOUNDARY: Internal sign-off only; zero external SMS/email dispatch.
    """
    try:
        return operator_service.approve_acknowledgement(db, complaint_id, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve acknowledgement: {str(e)}")
