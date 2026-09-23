"""
Triage Pipeline Orchestrator for NagarSetu
Coordinates raw complaint processing through multimodal extraction, AI classification,
locality normalization, deterministic urgency scoring with safety overrides, explainable routing,
and audit status logging, while enforcing raw data immutability.
"""

from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.schemas.triage import (
    AIClassificationResult,
    UrgencyEvaluationResult,
    LocalityNormalizationResult,
    ExplainableRoutingResult,
    ReviewFlagsResult,
    TriageAuditMetadata,
    ComplaintTriageResponse
)
from app.schemas.complaint import UrgencyLevel, ProcessingStatus
from app.services.classification.classifier import ClassificationService
from app.services.classification.gemini_client import GeminiClassificationClient
from app.rules.urgency_engine import UrgencyEngine
from app.rules.locality_normalizer import LocalityNormalizer
from app.rules.routing_engine import RoutingEngine
from app.rules.confidence_evaluator import ConfidenceEvaluator

logger = logging.getLogger("nagarsetu.triage_service")


class TriageService:
    """
    Main orchestration engine executing the 7-step triage pipeline per complaint.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClassificationClient] = None
    ):
        self.classification_service = ClassificationService(client=gemini_client)
        self.urgency_engine = UrgencyEngine()
        self.locality_normalizer = LocalityNormalizer()
        self.routing_engine = RoutingEngine()
        self.confidence_evaluator = ConfidenceEvaluator()

    def process_complaint(
        self,
        complaint_id: str,
        db: Session,
        reprocess: bool = False
    ) -> TriagedComplaint:
        """
        Processes a complaint through the end-to-end triage pipeline.
        Idempotent: if already processed and reprocess is False, returns existing record.
        """
        # 1. Retrieve Raw Complaint (Strictly Read-Only)
        raw_complaint = db.query(RawComplaint).filter(
            RawComplaint.complaint_id == complaint_id
        ).first()

        if not raw_complaint:
            raise ValueError(f"Complaint record '{complaint_id}' not found in raw_complaints.")

        # 2. Retrieve existing TriagedComplaint
        triaged = db.query(TriagedComplaint).filter(
            TriagedComplaint.complaint_id == complaint_id
        ).first()

        old_status = "PREPROCESSED"
        if triaged:
            old_status = triaged.processing_status
            if not reprocess and triaged.processing_status not in ["RAW", "PREPROCESSED"]:
                logger.info(
                    "Complaint '%s' is already triaged (status: %s). Skipping without reprocess.",
                    complaint_id, triaged.processing_status
                )
                return triaged
        else:
            # Create stub if somehow missing
            triaged = TriagedComplaint(
                complaint_id=complaint_id,
                processing_status="PREPROCESSED"
            )
            db.add(triaged)
            db.flush()

        # 3. Extract Multimodal Content
        text_content = raw_complaint.text or ""
        speech_transcription = None
        image_caption = raw_complaint.image_caption

        if triaged.multimodal_payload and isinstance(triaged.multimodal_payload, dict):
            speech_transcription = triaged.multimodal_payload.get("speech_transcription")
            if not speech_transcription and isinstance(triaged.multimodal_payload.get("audio"), dict):
                speech_transcription = triaged.multimodal_payload["audio"].get("transcription")
            if not image_caption:
                image_caption = triaged.multimodal_payload.get("image_caption")
            if not image_caption and isinstance(triaged.multimodal_payload.get("image"), dict):
                image_caption = triaged.multimodal_payload["image"].get("caption")

        primary_text = text_content or speech_transcription or image_caption or ""

        # 4. Step 1: AI Classification
        ai_result: AIClassificationResult = self.classification_service.classify(
            complaint_text=primary_text,
            speech_transcription=speech_transcription,
            image_caption=image_caption,
            channel=raw_complaint.channel or "municipal_app",
            metadata=getattr(raw_complaint, "extra_metadata", None)
        )

        # 5. Step 2: Locality Normalization
        locality_result: LocalityNormalizationResult = self.locality_normalizer.normalize(
            source_location_hint=raw_complaint.source_location,
            complaint_text=primary_text,
            ai_extracted_locality=None,
            db=db
        )

        # 6. Step 3: Deterministic Urgency & Safety Overrides
        urgency_result: UrgencyEvaluationResult = self.urgency_engine.evaluate(
            complaint_text=primary_text,
            category_id=ai_result.category,
            ai_classification=ai_result
        )

        # 7. Step 4: Explainable Routing
        routing_result: ExplainableRoutingResult = self.routing_engine.route(
            predicted_department=ai_result.department,
            category_id=ai_result.category,
            routing_terms=ai_result.routing_terms,
            complaint_text=primary_text,
            locality_info=locality_result
        )

        # 8. Step 5: Confidence & Review Flags Evaluation
        category_valid = routing_result.routing_rule_id != "ROUTE_UNKNOWN_FALLBACK"
        review_flags: ReviewFlagsResult = self.confidence_evaluator.evaluate(
            classification_confidence=ai_result.confidence,
            routing_confidence=routing_result.routing_confidence,
            locality_confidence=locality_result.confidence,
            safety_override_applied=urgency_result.safety_override_applied,
            category_valid=category_valid,
            locality_match_type=locality_result.match_type
        )

        # 9. Draft Human-in-the-Loop Acknowledgement Message (Rule 2.3)
        draft_acknowledgement = self._draft_acknowledgement(
            complaint_id=complaint_id,
            summary=ai_result.summary,
            department=routing_result.recommended_department,
            urgency=urgency_result.urgency.value,
            locality=locality_result.canonical_locality
        )

        # 10. Persist Derived TriagedComplaint
        now = datetime.now(timezone.utc)

        triaged.language = ai_result.language
        triaged.summary = ai_result.summary
        triaged.department = routing_result.recommended_department
        triaged.category = ai_result.category
        triaged.subcategory = ai_result.subcategory
        triaged.urgency = urgency_result.urgency.value
        triaged.urgency_score = urgency_result.urgency_score
        triaged.urgency_reason = urgency_result.urgency_reason
        triaged.normalized_locality = locality_result.canonical_locality
        triaged.ward = locality_result.ward
        triaged.zone = locality_result.zone
        triaged.routing_evidence = ", ".join(routing_result.routing_evidence)
        triaged.routing_confidence = routing_result.routing_confidence
        triaged.processing_status = "OPERATOR_REVIEW_PENDING"
        triaged.model_version = self.classification_service.model_version
        triaged.prompt_version = self.classification_service.prompt_version
        triaged.processed_at = now

        # Package full audit metadata
        audit_meta = TriageAuditMetadata(
            classification=ai_result,
            urgency_breakdown=urgency_result,
            locality=locality_result,
            routing=routing_result,
            review_flags=review_flags,
            model_version=self.classification_service.model_version,
            prompt_version=self.classification_service.prompt_version,
            processed_at=now
        )
        triaged.triage_metadata = audit_meta.model_dump(mode="json")

        # 11. Record StatusHistory Audit Trail
        history_entry = StatusHistory(
            complaint_id=complaint_id,
            old_status=old_status,
            new_status="OPERATOR_REVIEW_PENDING",
            changed_by="system_ai_triage",
            timestamp=now,
            notes=f"Triage complete: {review_flags.review_reason}"
        )
        db.add(history_entry)

        db.commit()
        db.refresh(triaged)
        return triaged

    def _draft_acknowledgement(
        self,
        complaint_id: str,
        summary: str,
        department: str,
        urgency: str,
        locality: str
    ) -> str:
        """
        Drafts a polite, structured civic acknowledgement in English and Indic style.
        Adheres to Rule 2.3: requires human operator confirmation prior to sending.
        """
        loc_str = f"in {locality}" if locality and locality != "UNKNOWN" else ""
        return (
            f"Dear Citizen, your grievance regarding '{summary}' {loc_str} has been registered "
            f"under Ticket #{complaint_id}. It has been prioritized as {urgency} and assigned "
            f"to the {department} Department for field action. [DRAFT - Pending Operator Approval]"
        )

    @staticmethod
    def build_triage_response(
        triaged: TriagedComplaint,
        raw: RawComplaint
    ) -> ComplaintTriageResponse:
        """Helper to construct ComplaintTriageResponse from database records."""
        metadata = triaged.triage_metadata or {}
        audit_meta = TriageAuditMetadata.model_validate(metadata)

        draft = (
            f"Dear Citizen, your grievance regarding '{triaged.summary}' has been registered "
            f"under Ticket #{raw.complaint_id}. It has been prioritized as {triaged.urgency} and assigned "
            f"to the {triaged.department} Department. [DRAFT - Pending Operator Approval]"
        )

        return ComplaintTriageResponse(
            complaint_id=raw.complaint_id,
            original_channel=raw.channel,
            original_text=raw.text or raw.image_caption or "",
            processing_status=ProcessingStatus(triaged.processing_status),
            language=triaged.language or "en",
            summary=triaged.summary or "",
            department=triaged.department or "DEPT_SWM",
            category=triaged.category or "",
            subcategory=triaged.subcategory,
            urgency=UrgencyLevel(triaged.urgency or "MEDIUM"),
            urgency_score=triaged.urgency_score or 0.5,
            urgency_reason=triaged.urgency_reason or "",
            normalized_locality=triaged.normalized_locality or "UNKNOWN",
            ward=triaged.ward,
            zone=triaged.zone,
            routing_evidence=triaged.routing_evidence or "",
            routing_confidence=triaged.routing_confidence or 0.0,
            acknowledgement_draft=draft,
            triage_audit=audit_meta,
            processed_at=triaged.processed_at
        )
