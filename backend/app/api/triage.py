"""
Triage API Router for NagarSetu
Provides endpoints for executing AI classification, deterministic urgency scoring,
explainable routing, and retrieving comprehensive triage audit breakdowns.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.complaint import RawComplaint, TriagedComplaint
from app.schemas.triage import ComplaintTriageResponse
from app.services.triage.triage_service import TriageService

logger = logging.getLogger("nagarsetu.api.triage")
router = APIRouter(prefix="/complaints", tags=["Triage Pipeline"])


def get_triage_service() -> TriageService:
    return TriageService()


@router.post(
    "/{complaint_id}/process",
    response_model=ComplaintTriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute automated triage on a complaint"
)
def process_complaint_endpoint(
    complaint_id: str,
    db: Session = Depends(get_db),
    triage_service: TriageService = Depends(get_triage_service)
):
    """
    Executes the full triage pipeline for a specific raw complaint:
    1. Multimodal extraction
    2. AI classification & taxonomy validation
    3. Locality normalization against gazetteer
    4. Deterministic urgency scoring with mandatory safety overrides
    5. Explainable routing recommendation
    6. Operator review flag assignment
    7. Derived ticket persistence and audit logging
    """
    raw = db.query(RawComplaint).filter(RawComplaint.complaint_id == complaint_id).first()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID '{complaint_id}' was not found."
        )

    try:
        triaged = triage_service.process_complaint(complaint_id=complaint_id, db=db, reprocess=False)
        return TriageService.build_triage_response(triaged=triaged, raw=raw)
    except Exception as exc:
        logger.exception("Triage pipeline failed for complaint %s: %s", complaint_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process complaint: {str(exc)}"
        )


@router.get(
    "/{complaint_id}/triage",
    response_model=ComplaintTriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve detailed triage audit breakdown"
)
def get_complaint_triage_endpoint(
    complaint_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves the complete triage evaluation for a complaint, including
    sub-scores (safety, outage, duration), safety override triggers,
    gazetteer match details, routing evidence, and operator review flags.
    """
    raw = db.query(RawComplaint).filter(RawComplaint.complaint_id == complaint_id).first()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID '{complaint_id}' was not found."
        )

    triaged = db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == complaint_id).first()
    if not triaged or not triaged.triage_metadata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Complaint '{complaint_id}' has not been triaged yet. Call /process first."
        )

    return TriageService.build_triage_response(triaged=triaged, raw=raw)


@router.post(
    "/{complaint_id}/reprocess",
    response_model=ComplaintTriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Force re-execution of automated triage"
)
def reprocess_complaint_endpoint(
    complaint_id: str,
    db: Session = Depends(get_db),
    triage_service: TriageService = Depends(get_triage_service)
):
    """
    Forces re-execution of the triage pipeline even if already processed.
    Useful when taxonomy, routing rules, or prompts are updated.
    """
    raw = db.query(RawComplaint).filter(RawComplaint.complaint_id == complaint_id).first()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID '{complaint_id}' was not found."
        )

    try:
        triaged = triage_service.process_complaint(complaint_id=complaint_id, db=db, reprocess=True)
        return TriageService.build_triage_response(triaged=triaged, raw=raw)
    except Exception as exc:
        logger.exception("Triage reprocessing failed for complaint %s: %s", complaint_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reprocess complaint: {str(exc)}"
        )
