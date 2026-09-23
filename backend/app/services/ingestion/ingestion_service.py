"""
Core Ingestion Orchestration Service for NagarSetu.
Coordinates parsing, column mapping, validation, raw database persistence,
multimodal preprocessing, and initial triage staging while enforcing raw immutability.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.services.ingestion.csv_parser import CSVParser
from app.services.ingestion.column_mapper import ColumnMapper
from app.services.ingestion.validator import IngestionValidator
from app.services.preprocessing.multimodal import MultimodalPreprocessor
from app.schemas.api_contracts import BatchIngestSummaryResponse, RejectedRowDetail


class IngestionService:
    """
    High-level service managing complaint batch imports.
    """

    def __init__(self, db: Session, custom_column_mapping: Optional[Dict[str, str]] = None):
        self.db = db
        self.column_mapper = ColumnMapper(custom_mapping=custom_column_mapping)
        self.validator = IngestionValidator()

    def ingest_csv_bytes(self, content_bytes: bytes, file_name: str = "upload.csv") -> BatchIngestSummaryResponse:
        """Parses CSV bytes and ingests complaints."""
        raw_rows, parse_warnings = CSVParser.parse_bytes(content_bytes)
        return self._process_rows(raw_rows, file_name=file_name, initial_warnings=parse_warnings)

    def ingest_csv_file(self, file_path: Union[str, Path]) -> BatchIngestSummaryResponse:
        """Reads a CSV file from disk and ingests complaints."""
        path = Path(file_path)
        raw_rows, parse_warnings = CSVParser.parse_file(path)
        return self._process_rows(raw_rows, file_name=path.name, initial_warnings=parse_warnings)

    def ingest_row_dicts(self, rows: List[Dict[str, Any]], batch_source_name: str = "batch_json") -> BatchIngestSummaryResponse:
        """Directly processes a list of raw dictionaries."""
        return self._process_rows(rows, file_name=batch_source_name, initial_warnings=[])

    def _process_rows(
        self,
        raw_rows: List[Dict[str, Any]],
        file_name: str,
        initial_warnings: List[str]
    ) -> BatchIngestSummaryResponse:
        """
        Internal loop iterating over raw rows, mapping, validating, and persisting.
        """
        import_id = f"IMP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        self.validator.reset_batch()

        total_rows = len(raw_rows)
        accepted_rows = 0
        rejected_rows = 0
        duplicate_ids: List[str] = []
        missing_content_rows: List[int] = []
        warnings: List[str] = list(initial_warnings)
        rejected_details: List[RejectedRowDetail] = []

        text_only_count = 0
        voice_count = 0
        image_count = 0
        multimodal_count = 0
        created_complaints_count = 0

        # Query existing IDs in database to enforce idempotency
        candidate_ids = set()
        for r in raw_rows:
            mapped_temp, _ = self.column_mapper.map_row(r)
            if mapped_temp.get("complaint_id"):
                candidate_ids.add(str(mapped_temp["complaint_id"]).strip())

        existing_db_ids = set()
        if candidate_ids:
            existing_records = self.db.query(RawComplaint.complaint_id).filter(
                RawComplaint.complaint_id.in_(candidate_ids)
            ).all()
            existing_db_ids = {rec[0] for rec in existing_records}

        now_utc = datetime.now(timezone.utc)

        for idx, raw_row in enumerate(raw_rows, start=1):
            # 1. Map columns into canonical dictionary + extra metadata
            canonical_data, extra_metadata = self.column_mapper.map_row(raw_row)

            # 2. Validate row
            validation = self.validator.validate_row(idx, canonical_data)
            warnings.extend(validation.warnings)

            if not validation.is_valid:
                rejected_rows += 1
                cid = canonical_data.get("complaint_id")
                reason = validation.rejection_reason or "Unknown validation error"
                if "Missing all complaint content" in reason:
                    missing_content_rows.append(idx)
                if "Duplicate complaint ID" in reason and cid:
                    duplicate_ids.append(str(cid))

                raw_snippet = str(raw_row)[:120]
                rejected_details.append(RejectedRowDetail(
                    row_index=idx,
                    complaint_id=str(cid) if cid else None,
                    reason=reason,
                    raw_snippet=raw_snippet
                ))
                continue

            cid = str(canonical_data["complaint_id"]).strip()

            # 3. Check database idempotency: if complaint already exists, skip insertion
            if cid in existing_db_ids:
                duplicate_ids.append(cid)
                warnings.append(f"Row {idx}: Complaint '{cid}' already exists in database. Skipped duplicate insertion.")
                rejected_rows += 1
                rejected_details.append(RejectedRowDetail(
                    row_index=idx,
                    complaint_id=cid,
                    reason="Complaint already exists in database (idempotent skip).",
                    raw_snippet=str(raw_row)[:120]
                ))
                continue

            # 4. Multimodal preprocessing
            multimodal_payload, modality_category = MultimodalPreprocessor.preprocess(canonical_data)
            if modality_category == "text_only":
                text_only_count += 1
            elif modality_category == "voice":
                voice_count += 1
            elif modality_category == "image":
                image_count += 1
            elif modality_category == "multimodal":
                multimodal_count += 1

            # 5. Insert immutable RawComplaint
            complaint_timestamp = validation.parsed_timestamp or now_utc
            raw_record = RawComplaint(
                complaint_id=cid,
                timestamp=complaint_timestamp,
                channel=canonical_data.get("channel") or "state_helpline",
                text=canonical_data.get("text"),
                audio_path=canonical_data.get("audio_path"),
                image_path=canonical_data.get("image_path"),
                image_caption=canonical_data.get("image_caption"),
                source_location=canonical_data.get("source_location"),
                department_label=canonical_data.get("department_label"),
                category_label=canonical_data.get("category_label"),
                urgency_label=canonical_data.get("urgency_label"),
                created_at=now_utc
            )
            self.db.add(raw_record)
            self.db.flush()

            # 6. Insert initial RAW StatusHistory
            self.db.add(StatusHistory(
                complaint_id=cid,
                old_status=None,
                new_status="RAW",
                changed_by="ingestion_pipeline",
                timestamp=now_utc,
                notes=f"Ingested from '{file_name}' (Import: {import_id})"
            ))

            # 7. Insert Staged TriagedComplaint with PREPROCESSED status
            sample_summary = canonical_data.get("text")
            if sample_summary:
                summary_text = (sample_summary[:140] + "...") if len(sample_summary) > 140 else sample_summary
            elif canonical_data.get("image_caption"):
                summary_text = f"[Image Grievance] {canonical_data['image_caption']}"
            elif canonical_data.get("audio_path"):
                summary_text = "[Voice Note Grievance - Transcription Pending]"
            else:
                summary_text = "[Multimodal Grievance]"

            triaged_record = TriagedComplaint(
                complaint_id=cid,
                language=None,  # Handled in future classification pipeline
                summary=summary_text,
                department=canonical_data.get("department_label"),
                category=canonical_data.get("category_label"),
                subcategory=None,
                urgency=canonical_data.get("urgency_label") or "LOW",
                urgency_score=0.0,
                urgency_reason="Pending Phase 4 triage assessment",
                normalized_locality=canonical_data.get("source_location") or "UNSPECIFIED",
                ward=None,
                zone=None,
                duplicate_cluster_id=None,
                duplicate_confidence=None,
                routing_evidence="Pending Phase 4 AI routing & explainability",
                routing_confidence=0.0,
                acknowledgement_id=None,
                processing_status="PREPROCESSED",
                model_version="preprocessor-v1.0",
                prompt_version="raw-ingest-v1",
                multimodal_payload=multimodal_payload,
                processed_at=now_utc
            )
            self.db.add(triaged_record)

            # 8. Insert PREPROCESSED StatusHistory
            self.db.add(StatusHistory(
                complaint_id=cid,
                old_status="RAW",
                new_status="PREPROCESSED",
                changed_by="multimodal_preprocessor",
                timestamp=now_utc,
                notes=f"Multimodal preprocessing complete ({modality_category})."
            ))

            accepted_rows += 1
            created_complaints_count += 1
            existing_db_ids.add(cid)

        # Commit all accepted rows
        self.db.commit()

        message = (
            f"Successfully processed {total_rows} rows from '{file_name}': "
            f"{accepted_rows} accepted, {rejected_rows} rejected."
        )

        return BatchIngestSummaryResponse(
            import_id=import_id,
            file_name=file_name,
            total_rows=total_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            duplicate_ids=duplicate_ids,
            missing_content_rows=missing_content_rows,
            text_only_rows=text_only_count,
            voice_rows=voice_count,
            image_rows=image_count,
            multimodal_rows=multimodal_count,
            warnings=warnings,
            created_complaints_count=created_complaints_count,
            rejected_details=rejected_details,
            message=message
        )
