"""
Multimodal Preprocessing Service for NagarSetu.
Normalizes text, voice, and image inputs into a structured multimodal representation
ready for downstream AI triage, setting transcription and vision statuses to 'pending'.
"""

from typing import Dict, Any, List, Optional, Tuple


class MultimodalPreprocessor:
    """
    Constructs normalized multimodal representations and categorizes input modalities.
    """

    @classmethod
    def preprocess(cls, canonical_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Processes canonical complaint fields into a normalized multimodal dictionary
        and determines the record's primary modality type:
        ('text_only', 'voice', 'image', or 'multimodal').
        """
        complaint_id = canonical_data.get("complaint_id")
        text = canonical_data.get("text")
        audio_path = canonical_data.get("audio_path")
        image_path = canonical_data.get("image_path")
        image_caption = canonical_data.get("image_caption")

        has_text = bool(text and str(text).strip())
        has_audio = bool(audio_path and str(audio_path).strip())
        has_image = bool((image_path and str(image_path).strip()) or (image_caption and str(image_caption).strip()))

        modalities: List[str] = []
        if has_text:
            modalities.append("text")
        if has_audio:
            modalities.append("voice")
        if has_image:
            modalities.append("image")

        # Determine modality category for ingestion metric tracking
        if has_text and not has_audio and not has_image:
            modality_category = "text_only"
        elif has_audio and not has_image:
            modality_category = "voice"
        elif has_image and not has_audio:
            modality_category = "image"
        elif len(modalities) > 1:
            modality_category = "multimodal"
        else:
            modality_category = "text_only"

        # Construct normalized multimodal payload conforming to specification
        payload: Dict[str, Any] = {
            "complaint_id": complaint_id,
            "text": text,
            "language": None,  # Will be detected by language handling model in future phase
            "audio": {
                "path": audio_path,
                "transcription_status": "pending" if has_audio else "none"
            },
            "image": {
                "path": image_path,
                "caption": image_caption,
                "analysis_status": "pending" if has_image else "none"
            },
            "modalities": modalities,
            "modality_category": modality_category
        }

        return payload, modality_category
