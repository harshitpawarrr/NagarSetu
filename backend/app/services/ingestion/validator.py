"""
Validation Engine for NagarSetu Complaint Ingestion.
Enforces data integrity, complaint ID presence, modality presence,
and timestamp parsing while strictly preventing fabrication of missing content.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
import re

# Supported channel identifiers
VALID_CHANNELS = {
    "state_helpline",
    "municipal_app",
    "elected_rep_message",
    "social_media",
    "walk_in_petition"
}

# Common datetime format patterns
DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y"
]


class ValidationResult:
    """Stores the outcome of row validation."""
    def __init__(
        self,
        is_valid: bool,
        rejection_reason: Optional[str] = None,
        warnings: Optional[List[str]] = None,
        parsed_timestamp: Optional[datetime] = None
    ):
        self.is_valid = is_valid
        self.rejection_reason = rejection_reason
        self.warnings = warnings or []
        self.parsed_timestamp = parsed_timestamp


def parse_timestamp(raw_val: Any) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Attempts to parse arbitrary timestamp input into a timezone-aware UTC datetime.
    Returns (parsed_datetime, warning_string_if_failed).
    """
    if raw_val is None:
        return datetime.now(timezone.utc), None

    if isinstance(raw_val, datetime):
        if raw_val.tzinfo is None:
            return raw_val.replace(tzinfo=timezone.utc), None
        return raw_val, None

    str_val = str(raw_val).strip()
    if not str_val:
        return datetime.now(timezone.utc), None

    # Try ISO parsing first
    try:
        dt = datetime.fromisoformat(str_val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt, None
    except ValueError:
        pass

    # Try common formats
    for fmt in DATETIME_FORMATS:
        try:
            dt = datetime.strptime(str_val, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt, None
        except ValueError:
            continue

    # Graceful fallback without crashing: fallback to UTC now and add warning
    return datetime.now(timezone.utc), f"Could not parse timestamp '{str_val}'. Using ingestion time."


class IngestionValidator:
    """
    Validates mapped canonical complaint records for required content and integrity.
    """

    def __init__(self):
        self.seen_batch_ids: Set[str] = set()

    def reset_batch(self):
        """Resets in-memory tracking between batches."""
        self.seen_batch_ids.clear()

    def validate_row(self, row_index: int, canonical_data: Dict[str, Any]) -> ValidationResult:
        """
        Validates an individual mapped canonical dictionary.
        Returns a ValidationResult indicating whether row is accepted or rejected.
        """
        warnings: List[str] = []

        # 1. Validate complaint_id presence
        complaint_id = canonical_data.get("complaint_id")
        if not complaint_id or not str(complaint_id).strip():
            return ValidationResult(
                is_valid=False,
                rejection_reason=f"Row {row_index}: Missing mandatory complaint ID."
            )

        cid_clean = str(complaint_id).strip()

        # 2. Validate duplicate complaint_id within current batch
        if cid_clean in self.seen_batch_ids:
            return ValidationResult(
                is_valid=False,
                rejection_reason=f"Row {row_index}: Duplicate complaint ID '{cid_clean}' within same import batch."
            )
        self.seen_batch_ids.add(cid_clean)

        # 3. Validate usable complaint content (modality presence)
        # In adherence to spec: valid if text exists OR voice exists OR image exists.
        has_text = bool(canonical_data.get("text") and str(canonical_data["text"]).strip())
        has_audio = bool(canonical_data.get("audio_path") and str(canonical_data["audio_path"]).strip())
        has_image = bool(
            (canonical_data.get("image_path") and str(canonical_data["image_path"]).strip()) or
            (canonical_data.get("image_caption") and str(canonical_data["image_caption"]).strip())
        )

        if not (has_text or has_audio or has_image):
            return ValidationResult(
                is_valid=False,
                rejection_reason=f"Row {row_index} (ID: {cid_clean}): Missing all complaint content (no text, audio, or image)."
            )

        # 4. Parse timestamp
        parsed_dt, ts_warning = parse_timestamp(canonical_data.get("timestamp"))
        if ts_warning:
            warnings.append(f"Row {row_index} (ID: {cid_clean}): {ts_warning}")

        # 5. Channel sanity check
        channel = canonical_data.get("channel")
        if channel not in VALID_CHANNELS:
            warnings.append(f"Row {row_index} (ID: {cid_clean}): Unrecognized channel '{channel}'. Normalized to 'state_helpline'.")
            canonical_data["channel"] = "state_helpline"

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            parsed_timestamp=parsed_dt
        )
