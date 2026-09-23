"""
Mock Gemini Classification Client for NagarSetu Tests
Provides deterministic in-memory responses for all test scenarios without
ever making real network calls to Google Gemini API.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.classification.gemini_client import (
    GeminiClassificationClient,
    GeminiError,
    GeminiTimeoutError,
    GeminiResponseMalformedError
)


class MockGeminiClient(GeminiClassificationClient):
    """
    In-memory mock supporting simulated responses for English, Hindi, Hinglish,
    and failure modes (malformed JSON, missing fields, invalid categories, low confidence, errors).
    """

    def __init__(
        self,
        mode: str = "normal",
        custom_response: Optional[Dict[str, Any]] = None,
        configured: bool = True
    ):
        super().__init__(api_key="mock-api-key" if configured else "", model_name="mock-gemini")
        self.mode = mode
        self.custom_response = custom_response
        self._configured = configured

    def is_configured(self) -> bool:
        return self._configured

    def generate_structured_json(
        self,
        system_instruction: str,
        prompt: str
    ) -> Dict[str, Any]:
        """Returns deterministic mocked responses according to self.mode."""
        if not self.is_configured():
            from app.services.classification.gemini_client import GeminiNotConfiguredError
            raise GeminiNotConfiguredError("GEMINI_API_KEY is not configured in test.")

        if self.mode == "timeout":
            raise GeminiTimeoutError("Mock Gemini API call timed out after 15.0s.")

        if self.mode == "api_error":
            raise GeminiError("Mock Gemini internal server error (500).")

        if self.mode == "malformed_json":
            raise GeminiResponseMalformedError("Mock Gemini returned non-parseable garbage text.")

        if self.custom_response is not None:
            return self.custom_response

        # Extract the actual input complaint content from prompt
        content_part = prompt
        if "Content:" in prompt:
            content_part = prompt.split("Content:", 1)[1]
        elif "INPUT COMPLAINT RECORD:" in prompt:
            content_part = prompt.split("INPUT COMPLAINT RECORD:", 1)[1]
        elif "INPUT RECORD:" in prompt:
            content_part = prompt.split("INPUT RECORD:", 1)[1]

        content_lower = content_part.lower()

        # 0. Ambiguous / Low confidence (Priority Check)
        if "kuch bhi theek" in content_lower or "sab kharab" in content_lower or "ambiguous" in content_lower:
            return {
                "language": "hi-Latn",
                "summary": "Ambiguous complaint with unclear civic issue.",
                "department": "DEPT_SWM",
                "category": "CAT_GARBAGE_COLLECTION",
                "subcategory": None,
                "routing_terms": ["unclear"],
                "confidence": 0.35
            }

        # 1. Electrical / Street light / Live wire (English / Hindi / Hinglish)
        if (
            "street light" in content_lower or "streetlight" in content_lower or "bijli" in content_lower
            or "wire" in content_lower or "electrical" in content_lower or "pole" in content_lower
            or "स्ट्रीट लाइट" in content_part or "लाइट" in content_part or "बिजली" in content_part or "अंधेरा" in content_part
        ):
            if self.mode == "low_confidence":
                return {
                    "language": "hi-Latn",
                    "summary": "Street light issue reported with uncertain details.",
                    "department": "DEPT_ELEC",
                    "category": "CAT_STREET_LIGHTING",
                    "subcategory": None,
                    "routing_terms": ["street light"],
                    "confidence": 0.42
                }
            if self.mode == "missing_fields":
                # Omits department and summary
                return {
                    "language": "en",
                    "category": "CAT_STREET_LIGHTING",
                    "confidence": 0.88
                }
            if self.mode == "invalid_taxonomy":
                return {
                    "language": "en",
                    "summary": "Nonexistent department grievance.",
                    "department": "DEPT_NONEXISTENT",
                    "category": "CAT_NONEXISTENT",
                    "subcategory": None,
                    "routing_terms": ["street light"],
                    "confidence": 0.90
                }

            subcat = "SUB_LIVE_WIRE_EXPOSED" if "wire" in content_lower or "hazard" in content_lower else "SUB_STREETLIGHT_OUT"
            return {
                "language": "hi" if ("स्ट्रीट लाइट" in content_part or "वार्ड" in content_part or "बिजली" in content_part) else "hi-Latn" if ("din" in content_lower or "mein" in content_lower) else "en",
                "summary": "Exposed live electrical hazard reported." if "wire" in content_lower else "Street lights reported non-functional causing dark street condition.",
                "department": "DEPT_ELEC",
                "category": "CAT_STREET_LIGHTING",
                "subcategory": subcat,
                "routing_terms": ["wire", "hazard"] if "wire" in content_lower else ["street light", "band hai"],
                "confidence": 0.96 if "wire" in content_lower else 0.94
            }

        # 2. Sanitation / Garbage
        if "kachra" in content_lower or "garbage" in content_lower or "dustbin" in content_lower or "stench" in content_lower or "safai" in content_lower:
            return {
                "language": "en",
                "summary": "Overflowing garbage dump reported in locality.",
                "department": "DEPT_SWM",
                "category": "CAT_GARBAGE_COLLECTION",
                "subcategory": "SUB_DUMPSTER_OVERFLOW",
                "routing_terms": ["garbage", "kachra", "waste"],
                "confidence": 0.89
            }

        # 3. Horticulture / Fallen Tree
        if "tree" in content_lower or "branch" in content_lower or "ped" in content_lower or "park" in content_lower:
            return {
                "language": "en",
                "summary": "Heavy tree branch fallen on infrastructure.",
                "department": "DEPT_HORT",
                "category": "CAT_HORTICULTURE",
                "subcategory": "SUB_FALLEN_TREE",
                "routing_terms": ["tree", "branch", "fallen"],
                "confidence": 0.88
            }

        # 4. Devanagari Hindi / Contaminated Water / Sewer
        if "गंदा पानी" in content_part or "पानी" in content_part or "sewage" in content_lower or "water" in content_lower or "gutter" in content_lower or "paani" in content_lower:
            subcat = "SUB_SEWER_OVERFLOW" if ("sewage" in content_lower or "gutter" in content_lower) else "SUB_PIPE_BURST" if "pipeline" in content_lower else "SUB_CONTAMINATED_WATER"
            cat = "CAT_DRAINAGE_SEWAGE" if ("sewage" in content_lower or "gutter" in content_lower) else "CAT_WATER_SUPPLY"
            return {
                "language": "hi" if ("गंदा" in content_part or "पानी" in content_part) else "hi-Latn" if ("paani" in content_lower or "mein" in content_lower) else "en",
                "summary": "Water/sewer pipeline issue reported.",
                "department": "DEPT_WSS",
                "category": cat,
                "subcategory": subcat,
                "routing_terms": ["water", "sewage", "pipeline"],
                "confidence": 0.92
            }

        # 5. Roads / Pothole (Hinglish / English)
        if "pothole" in content_lower or "gaddha" in content_lower or "crater" in content_lower or "trench" in content_lower or "pavement" in content_lower or "पत्थर" in content_part or "सड़क" in content_part or "sadak" in content_lower:
            return {
                "language": "hi" if "सड़क" in content_part else "hi-Latn" if "mein" in content_lower or "hai" in content_lower else "en",
                "summary": "Deep pothole or damaged carriageway creating vehicular hazard.",
                "department": "DEPT_RDS",
                "category": "CAT_ROAD_MAINTENANCE",
                "subcategory": "SUB_POTHOLE",
                "routing_terms": ["pothole", "gaddha", "road"],
                "confidence": 0.91
            }

        # 6. Default generic response
        return {
            "language": "en",
            "summary": "Generic municipal civic grievance.",
            "department": "DEPT_SWM",
            "category": "CAT_GARBAGE_COLLECTION",
            "subcategory": None,
            "routing_terms": ["civic", "grievance"],
            "confidence": 0.80
        }
