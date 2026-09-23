"""
Configurable Column Mapper for NagarSetu Ingestion.
Maps varied source column names into canonical raw complaint fields
and preserves unknown columns in an extensible metadata dictionary.
"""

from typing import Dict, Any, Tuple, Optional

# Canonical field aliases (case-insensitive, underscore/space normalized)
CANONICAL_FIELD_ALIASES = {
    "complaint_id": [
        "complaint_id", "complaintid", "id", "ticket_id", "ticketid",
        "reference_id", "ref_id", "complaint_no", "ticket_number", "sr_no"
    ],
    "timestamp": [
        "timestamp", "date", "created_at", "reported_at", "complaint_date",
        "datetime", "incident_date", "time"
    ],
    "channel": [
        "channel", "source", "source_channel", "origin", "platform",
        "intake_channel", "complaint_source", "mode"
    ],
    "text": [
        "text", "description", "complaint", "complaint_text", "message",
        "details", "grievance", "issue", "problem", "body"
    ],
    "audio_path": [
        "audio_path", "audio", "voice_path", "voice_note", "audio_file",
        "recording", "voice", "audio_recording"
    ],
    "image_path": [
        "image_path", "image", "photo", "photo_path", "picture",
        "attachment", "image_url", "photo_url", "photo_file"
    ],
    "image_caption": [
        "image_caption", "photo_caption", "caption", "image_description", "photo_description"
    ],
    "source_location": [
        "source_location", "location", "address", "locality", "area",
        "ward_hint", "place", "colony", "landmark"
    ],
    "department_label": [
        "department_label", "department", "dept", "dept_label", "assigned_department"
    ],
    "category_label": [
        "category_label", "category", "cat", "cat_label", "subject", "sub_category"
    ],
    "urgency_label": [
        "urgency_label", "urgency", "priority", "severity", "urgency_level"
    ]
}

# Channel normalization mapping
CHANNEL_NORMALIZATION_MAP = {
    "state_helpline": [
        "state_helpline", "state helpline", "cm helpline", "cm_helpline",
        "helpline", "181", "state_portal", "cm_grievance"
    ],
    "municipal_app": [
        "municipal_app", "municipal app", "mobile app", "app",
        "citizen app", "e-nagarpalika", "nagar_app", "mobile_app"
    ],
    "elected_rep_message": [
        "elected_rep_message", "elected representative message", "rep message",
        "representative message", "mla", "corporator", "councillor", "rep_message",
        "parshad", "vidhayak"
    ],
    "social_media": [
        "social_media", "social media", "twitter", "x", "facebook",
        "instagram", "social", "tweet"
    ],
    "walk_in_petition": [
        "walk_in_petition", "walk-in petition", "walk_in", "walk-in",
        "petition", "desk", "office", "jan sunwai", "in_person"
    ]
}


def normalize_header(header: str) -> str:
    """Normalizes a header string by lowercasing and stripping whitespace/punctuation."""
    return header.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")


def normalize_channel(raw_channel: Optional[str]) -> str:
    """Normalizes arbitrary channel text into supported canonical channel string."""
    if not raw_channel or not raw_channel.strip():
        return "state_helpline"  # Sensible default if missing

    cleaned = raw_channel.strip().lower()
    for canonical, variations in CHANNEL_NORMALIZATION_MAP.items():
        if cleaned in variations:
            return canonical
        for var in variations:
            if var in cleaned:
                return canonical

    return "state_helpline"


class ColumnMapper:
    """
    Dynamically maps raw row dictionaries into canonical complaint fields.
    Preserves all unrecognized columns in a metadata bag.
    """

    def __init__(self, custom_mapping: Optional[Dict[str, str]] = None):
        self.custom_mapping = custom_mapping or {}
        # Inverted index from normalized header variation to canonical field name
        self._lookup: Dict[str, str] = {}
        for canonical, aliases in CANONICAL_FIELD_ALIASES.items():
            for alias in aliases:
                self._lookup[normalize_header(alias)] = canonical

    def map_row(self, raw_row: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Maps a single input dictionary into (canonical_fields, metadata_fields).
        """
        canonical: Dict[str, Any] = {
            "complaint_id": None,
            "timestamp": None,
            "channel": None,
            "text": None,
            "audio_path": None,
            "image_path": None,
            "image_caption": None,
            "source_location": None,
            "department_label": None,
            "category_label": None,
            "urgency_label": None,
        }
        metadata: Dict[str, Any] = {}

        for raw_header, raw_value in raw_row.items():
            # Clean string value
            cleaned_value = raw_value.strip() if isinstance(raw_value, str) else raw_value
            if cleaned_value == "":
                cleaned_value = None

            norm_header = normalize_header(raw_header)

            # 1. Check custom overrides
            if norm_header in self.custom_mapping:
                target_canonical = self.custom_mapping[norm_header]
                if target_canonical in canonical and canonical[target_canonical] is None:
                    canonical[target_canonical] = cleaned_value
                    continue

            # 2. Check canonical alias lookup
            if norm_header in self._lookup:
                target_canonical = self._lookup[norm_header]
                if canonical[target_canonical] is None and cleaned_value is not None:
                    canonical[target_canonical] = cleaned_value
                    continue

            # 3. If unmapped, preserve in metadata
            if cleaned_value is not None:
                metadata[raw_header] = cleaned_value

        # Normalize channel if present
        if canonical["channel"]:
            canonical["channel"] = normalize_channel(str(canonical["channel"]))

        return canonical, metadata
