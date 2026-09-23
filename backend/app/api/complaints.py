"""
Complaints API Router for NagarSetu.
Provides endpoints for CSV batch ingestion, complaint listing with filters and pagination,
and individual ticket retrieval.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.models.acknowledgement import Acknowledgement
from app.schemas.complaint import (
    CanonicalComplaint,
    ComplaintChannel,
    UrgencyLevel,
    ProcessingStatus,
    MultimodalAttachment,
    InputModality
)
from app.schemas.api_contracts import (
    BatchIngestSummaryResponse,
    PaginatedComplaintList,
    PaginationMeta,
    BatchIngestRequest
)
from app.services.ingestion.ingestion_service import IngestionService

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def _to_canonical_schema(raw: RawComplaint, triaged: Optional[TriagedComplaint], ack: Optional[Acknowledgement]) -> CanonicalComplaint:
    """Helper converting ORM models into canonical Pydantic schema."""
    # Build attachments from raw multimodal paths
    attachments: List[MultimodalAttachment] = []
    if raw.audio_path:
        transcription_text = None
        if triaged and triaged.multimodal_payload and isinstance(triaged.multimodal_payload, dict):
            transcription_text = triaged.multimodal_payload.get("speech_transcription")
            if not transcription_text and isinstance(triaged.multimodal_payload.get("audio"), dict):
                transcription_text = triaged.multimodal_payload["audio"].get("transcription")
        attachments.append(MultimodalAttachment(
            modality=InputModality.VOICE,
            file_uri=raw.audio_path,
            transcription=transcription_text
        ))
    if raw.image_path or raw.image_caption:
        attachments.append(MultimodalAttachment(
            modality=InputModality.IMAGE_CAPTION,
            file_uri=raw.image_path,
            caption=raw.image_caption
        ))

    # Safe enum parsing
    channel_val = ComplaintChannel.STATE_HELPLINE
    try:
        if raw.channel:
            channel_val = ComplaintChannel(raw.channel)
    except ValueError:
        pass

    urgency_val = UrgencyLevel.LOW
    if triaged and triaged.urgency:
        try:
            urgency_val = UrgencyLevel(triaged.urgency)
        except ValueError:
            pass
    elif raw.urgency_label:
        try:
            urgency_val = UrgencyLevel(raw.urgency_label.upper())
        except ValueError:
            pass

    status_val = ProcessingStatus.RAW
    if triaged and triaged.processing_status:
        try:
            status_val = ProcessingStatus(triaged.processing_status)
        except ValueError:
            pass

    ack_draft = ""
    if ack:
        ack_draft = ack.draft_text
    elif triaged:
        ack_draft = f"Grievance {raw.complaint_id} recorded in {triaged.department or 'General'}. Awaiting review."

    return CanonicalComplaint(
        complaint_id=raw.complaint_id,
        original_channel=channel_val,
        original_text=raw.text or raw.image_caption or "[Voice Recording Grievance]",
        language=triaged.language if (triaged and triaged.language) else "en",
        summary=triaged.summary if (triaged and triaged.summary) else (raw.text[:100] if raw.text else "Raw civic grievance"),
        department=triaged.department if (triaged and triaged.department) else (raw.department_label or "DEPT_OTHER"),
        category=triaged.category if (triaged and triaged.category) else (raw.category_label or "CAT_GENERAL"),
        subcategory=triaged.subcategory if triaged else None,
        urgency=urgency_val,
        urgency_score=triaged.urgency_score if (triaged and triaged.urgency_score is not None) else 0.0,
        urgency_reason=triaged.urgency_reason if (triaged and triaged.urgency_reason) else "Pending Phase 4 triage",
        normalized_locality=triaged.normalized_locality if (triaged and triaged.normalized_locality) else (raw.source_location or "UNSPECIFIED"),
        ward=triaged.ward if triaged else None,
        zone=triaged.zone if triaged else None,
        duplicate_cluster_id=triaged.duplicate_cluster_id if triaged else None,
        duplicate_confidence=triaged.duplicate_confidence if triaged else None,
        routing_evidence=triaged.routing_evidence if (triaged and triaged.routing_evidence) else "Pending AI triage",
        routing_confidence=triaged.routing_confidence if (triaged and triaged.routing_confidence is not None) else 0.0,
        acknowledgement_draft=ack_draft,
        created_at=raw.created_at,
        processing_status=status_val,
        attachments=attachments,
        metadata={"raw_source_location": raw.source_location}
    )


@router.post(
    "/batch-ingest",
    response_model=BatchIngestSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of exported complaints via CSV upload"
)
async def batch_ingest_csv(
    file: UploadFile = File(..., description="Exported CSV file containing civic complaints"),
    db: Session = Depends(get_db)
):
    """
    Accepts an exported CSV dataset, maps columns, validates records,
    stores raw records immutably, and generates multimodal preprocessing representations.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format: '{file.filename}'. Currently CSV files (.csv) are supported."
        )

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV file is empty."
        )

    ingestion_service = IngestionService(db)
    result = ingestion_service.ingest_csv_bytes(content_bytes, file_name=file.filename)
    return result


@router.post(
    "/batch-ingest-json",
    response_model=BatchIngestSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of exported complaints via JSON payload"
)
def batch_ingest_json(
    payload: BatchIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Accepts a structured JSON batch payload for programmatic ingestion.
    """
    rows = []
    for item in payload.items:
        row_dict = {
            "complaint_id": item.source_reference_id,
            "channel": item.original_channel.value if hasattr(item.original_channel, "value") else str(item.original_channel),
            "text": item.raw_text,
            "timestamp": item.reported_at.isoformat() if item.reported_at else None,
            "source_location": item.raw_locality_hint
        }
        for att in item.attachments:
            if att.modality == InputModality.VOICE:
                row_dict["audio_path"] = att.file_uri
            elif att.modality == InputModality.IMAGE_CAPTION:
                row_dict["image_path"] = att.file_uri
                row_dict["image_caption"] = att.caption
        rows.append(row_dict)

    ingestion_service = IngestionService(db)
    return ingestion_service.ingest_row_dicts(rows, batch_source_name=payload.batch_source_name)


@router.get(
    "",
    response_model=PaginatedComplaintList,
    summary="List complaints with filtering and pagination"
)
def list_complaints(
    department: Optional[str] = Query(None, description="Filter by department code (e.g. DEPT_ROADS)"),
    category: Optional[str] = Query(None, description="Filter by category ID"),
    urgency: Optional[UrgencyLevel] = Query(None, description="Filter by urgency level"),
    status: Optional[ProcessingStatus] = Query(None, description="Filter by processing status"),
    ward: Optional[str] = Query(None, description="Filter by ward ID or name"),
    zone: Optional[str] = Query(None, description="Filter by zone name"),
    search_query: Optional[str] = Query(None, description="Free text search in complaint text and summary"),
    cluster_id: Optional[str] = Query(None, description="Filter by duplicate cluster ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Returns a paginated list of canonical complaints matching the provided criteria.
    """
    query = db.query(RawComplaint).outerjoin(TriagedComplaint, RawComplaint.complaint_id == TriagedComplaint.complaint_id)

    if department:
        query = query.filter(or_(TriagedComplaint.department == department, RawComplaint.department_label == department))
    if category:
        query = query.filter(or_(TriagedComplaint.category == category, RawComplaint.category_label == category))
    if urgency:
        query = query.filter(or_(TriagedComplaint.urgency == urgency.value, RawComplaint.urgency_label == urgency.value))
    if status:
        query = query.filter(TriagedComplaint.processing_status == status.value)
    if ward:
        query = query.filter(TriagedComplaint.ward == ward)
    if zone:
        query = query.filter(TriagedComplaint.zone == zone)
    if cluster_id:
        query = query.filter(TriagedComplaint.duplicate_cluster_id == cluster_id)
    if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        query = query.filter(or_(RawComplaint.text.ilike(term), TriagedComplaint.summary.ilike(term), RawComplaint.source_location.ilike(term)))

    total_records = query.count()
    total_pages = max(1, (total_records + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    records = query.order_by(RawComplaint.created_at.desc()).offset(offset).limit(page_size).all()

    # Pre-fetch acknowledgements for these records
    cids = [r.complaint_id for r in records]
    acks = db.query(Acknowledgement).filter(Acknowledgement.complaint_id.in_(cids)).all() if cids else []
    ack_map = {a.complaint_id: a for a in acks}

    canonical_list: List[CanonicalComplaint] = []
    for raw in records:
        canonical_list.append(_to_canonical_schema(raw, raw.triaged_record, ack_map.get(raw.complaint_id)))

    return PaginatedComplaintList(
        data=canonical_list,
        pagination=PaginationMeta(
            total_records=total_records,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get(
    "/{complaint_id}",
    response_model=CanonicalComplaint,
    summary="Get single complaint by ID"
)
def get_complaint(
    complaint_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves a single canonical complaint by complaint ID.
    """
    raw = db.query(RawComplaint).filter(RawComplaint.complaint_id == complaint_id).first()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID '{complaint_id}' not found."
        )

    ack = db.query(Acknowledgement).filter(Acknowledgement.complaint_id == complaint_id).first()
    return _to_canonical_schema(raw, raw.triaged_record, ack)
