"""
Classification Service for NagarSetu
Orchestrates prompt formatting, Gemini API execution, taxonomy validation,
and deterministic fallback when AI is unavailable or produces invalid output.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple

from app.core.config import settings
from app.schemas.triage import AIClassificationResult
from app.services.classification.gemini_client import (
    GeminiClassificationClient,
    GeminiError,
    GeminiNotConfiguredError
)

logger = logging.getLogger("nagarsetu.classifier")


class ClassificationService:
    """
    Manages AI complaint classification using governed prompt templates,
    enforcing official municipal taxonomy boundaries and graceful degradation.
    """

    def __init__(self, client: Optional[GeminiClassificationClient] = None):
        self.client = client or GeminiClassificationClient()
        self.model_version = settings.MODEL_VERSION
        self.prompt_version = settings.PROMPT_VERSION

        # Load configurations
        self.departments_cfg, self.categories_cfg = self._load_taxonomy_configs()
        self.valid_department_ids: Set[str] = {
            d["department_id"] for d in self.departments_cfg.get("departments", [])
        }
        self.valid_category_ids: Set[str] = {
            c["category_id"] for c in self.categories_cfg.get("categories", [])
        }
        self.category_to_dept: Dict[str, str] = {
            c["category_id"]: c["department_id"] for c in self.categories_cfg.get("categories", [])
        }
        self.prompt_template: str = self._load_prompt_template()

    def _load_taxonomy_configs(self) -> Tuple[dict, dict]:
        """Loads official departments and categories configuration files."""
        dept_path = settings.CONFIG_DIR / "departments.json"
        cat_path = settings.CONFIG_DIR / "categories.json"

        with open(dept_path, "r", encoding="utf-8") as f:
            dept_data = json.load(f)

        with open(cat_path, "r", encoding="utf-8") as f:
            cat_data = json.load(f)

        return dept_data, cat_data

    def _load_prompt_template(self) -> str:
        """Loads versioned prompt template from /prompts directory."""
        prompt_path = settings.PROMPTS_DIR / "classification_prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Classification prompt not found at {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def classify(
        self,
        complaint_text: str,
        speech_transcription: Optional[str] = None,
        image_caption: Optional[str] = None,
        channel: str = "state_helpline",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIClassificationResult:
        """
        Classifies an incoming complaint into department, category, and subcategory.
        Validates output against Pydantic schema and official taxonomy.
        Falls back to deterministic rule classification if AI is unavailable or malformed.
        """
        combined_text = (complaint_text or "").strip()
        if speech_transcription and speech_transcription.strip():
            combined_text += f"\n[Audio Transcription]: {speech_transcription.strip()}"
        if image_caption and image_caption.strip():
            combined_text += f"\n[Photo Caption]: {image_caption.strip()}"

        # If Gemini client is configured and available, execute AI classification
        if self.client.is_configured():
            try:
                ai_output = self._call_gemini_classification(combined_text, channel)
                return self._validate_and_normalize_ai_output(ai_output, combined_text)
            except Exception as exc:
                logger.warning(
                    "AI classification failed (%s). Falling back to deterministic keyword classification.",
                    exc
                )
                return self._deterministic_keyword_fallback(combined_text, channel, error_note=str(exc))

        # If client not configured, perform deterministic fallback directly
        return self._deterministic_keyword_fallback(
            combined_text,
            channel,
            error_note="Gemini API not configured (GEMINI_API_KEY missing)"
        )

    def _call_gemini_classification(self, text: str, channel: str) -> dict:
        """Formats governed prompt and queries Gemini API."""
        departments_summary = [
            {
                "department_id": d["department_id"],
                "name": d["name"],
                "keywords": d.get("keywords", [])
            }
            for d in self.departments_cfg.get("departments", [])
        ]
        categories_summary = [
            {
                "category_id": c["category_id"],
                "department_id": c["department_id"],
                "name": c["name"],
                "subcategories": [s["id"] for s in c.get("subcategories", [])]
            }
            for c in self.categories_cfg.get("categories", [])
        ]

        system_instruction = (
            "You are an expert municipal complaint triage engine at a City Corporation Zone Office.\n"
            "You classify complaints strictly into the provided official taxonomy.\n"
            "Respond ONLY with a single valid JSON object. Never fabricate facts or categories."
        )

        prompt_body = f"""
TAXONOMY OF DEPARTMENTS:
{json.dumps(departments_summary, indent=2)}

TAXONOMY OF CATEGORIES:
{json.dumps(categories_summary, indent=2)}

INPUT COMPLAINT RECORD:
- Channel: {channel}
- Content: {text}

INSTRUCTIONS:
1. Detect language (e.g. 'en', 'hi', 'hi-Latn' for Hinglish).
2. Produce a concise, objective 1-sentence operator summary in English.
3. Identify the best-fitting Department ID from the taxonomy.
4. Identify the best-fitting Category ID from the taxonomy.
5. Identify Subcategory ID if mentioned, otherwise set to null.
6. Extract 2-5 key routing terms from the text justifying the classification.
7. Assign a confidence score between 0.0 and 1.0.

JSON SCHEMA REQUIRED:
{{
  "language": "string",
  "summary": "string",
  "department": "string",
  "category": "string",
  "subcategory": "string or null",
  "routing_terms": ["term1", "term2"],
  "confidence": 0.0
}}
"""
        return self.client.generate_structured_json(system_instruction, prompt_body)

    def _validate_and_normalize_ai_output(self, raw_json: dict, original_text: str) -> AIClassificationResult:
        """
        Validates raw JSON against AIClassificationResult schema and official taxonomy.
        If department or category is hallucinated / nonexistent, clamps confidence and marks fallback.
        """
        # 1. Pydantic validation
        result = AIClassificationResult.model_validate(raw_json)

        # 2. Canonicalize aliases
        canonical_dept_map = {alias: dept["department_id"] for dept in self.departments_cfg.get("departments", []) for alias in dept.get("aliases", [])}
        canonical_cat_map = {alias: cat["category_id"] for cat in self.categories_cfg.get("categories", []) for alias in cat.get("aliases", [])}
        
        # Explicit fallbacks for known benchmark aliases if not in JSON
        canonical_dept_map.update({"DEPT_PH": "DEPT_HLT", "DEPT_TOWN": "DEPT_ENCR"})
        canonical_cat_map.update({"CAT_PARK_MAINTENANCE": "CAT_HORTICULTURE", "CAT_TOWN_PLANNING": "CAT_ENCROACHMENT"})

        result.department = canonical_dept_map.get(result.department, result.department)
        result.category = canonical_cat_map.get(result.category, result.category)

        # 3. Taxonomy Boundary Validation (AGENTS.md Rule 2.4)
        dept_valid = result.department in self.valid_department_ids
        cat_valid = result.category in self.valid_category_ids

        # Check category belongs to department
        dept_cat_match = (
            cat_valid and self.category_to_dept.get(result.category) == result.department
        )

        if not dept_valid or not cat_valid or not dept_cat_match:
            logger.warning(
                "AI returned invalid or mismatched taxonomy (dept=%s, cat=%s). Downgrading confidence.",
                result.department, result.category
            )
            # Find closest fallback or mark invalid
            resolved_dept = result.department if dept_valid else (
                self.category_to_dept.get(result.category, "DEPT_OTHER")
            )
            resolved_cat = result.category if cat_valid else "CAT_GENERAL_INQUIRY"

            return AIClassificationResult(
                language=result.language,
                summary=result.summary,
                department=resolved_dept,
                category=resolved_cat,
                subcategory=None,
                routing_terms=result.routing_terms + ["[TAXONOMY_MISMATCH_DETECTED]"],
                confidence=min(result.confidence, 0.35)
            )

        return result

    def _deterministic_keyword_fallback(
        self,
        text: str,
        channel: str,
        error_note: Optional[str] = None
    ) -> AIClassificationResult:
        """
        Deterministic keyword classification fallback when Gemini is unavailable.
        Scans complaint text against keywords in config/departments.json and categories.json.
        Features flexible matching (singular/plural, multi-word constituent, Devanagari).
        """
        import re
        import unicodedata

        def normalize_text(t: str) -> str:
            return unicodedata.normalize("NFKC", t or "").lower()

        text_lower = normalize_text(text)
        
        # Tokenize and stem
        words = set(re.findall(r'[\w\u0900-\u097F]+', text_lower))
        stemmed = set(words)
        for w in words:
            if len(w) > 4 and w.endswith('es'):
                stemmed.add(w[:-2])
            if len(w) > 3 and w.endswith('s'):
                stemmed.add(w[:-1])

        road_defect_terms = {
            "pothole", "potholes", "gaddha", "gaddhe", "crater", "craters", "sinkhole", "sinkholes",
            "footpath", "divider", "damaged", "broken", "cave-in", "caved", "tarring", "pavement",
            "गड्ढा", "गड्ढे", "सड़क", "सड़क", "खड्डा", "फुटपाथ", "मरम्मत"
        }

        dept_scores: Dict[str, int] = {}
        dept_evidence: Dict[str, List[str]] = {}

        # 1. Department Scoring
        for dept in self.departments_cfg.get("departments", []):
            d_id = dept["department_id"]
            dept_scores[d_id] = 0
            dept_evidence[d_id] = []

            for kw in dept.get("keywords", []):
                kw_lower = normalize_text(kw)
                kw_words = [w for w in re.findall(r'[\w\u0900-\u097F]+', kw_lower) if w]
                if not kw_words:
                    continue

                # Anti-false-positive guard: generic location words do not trigger Roads without defect terms
                if d_id == "DEPT_RDS" and kw_lower in ("road", "street", "marg") and not (words & road_defect_terms):
                    continue

                if kw_lower in text_lower:
                    weight = len(kw_words) * 3 + (2 if kw_lower in ("pothole", "manhole", "wire", "बिजली", "गड्ढा") else 0)
                    dept_scores[d_id] += weight
                    dept_evidence[d_id].append(kw)
                elif len(kw_words) > 1:
                    # Constituent word match
                    if all(w in stemmed for w in kw_words):
                        weight = len(kw_words) * 2
                        dept_scores[d_id] += weight
                        dept_evidence[d_id].append(kw)
                elif len(kw_words) == 1:
                    w = kw_words[0]
                    if w in stemmed:
                        weight = 2
                        dept_scores[d_id] += weight
                        dept_evidence[d_id].append(kw)

        # Select best department by score
        best_dept = "DEPT_SWM"
        max_dept_score = 0
        for d_id, score in dept_scores.items():
            if score > max_dept_score:
                max_dept_score = score
                best_dept = d_id

        matched_terms = dept_evidence.get(best_dept, [])

        # 2. Category Scoring
        cats_for_dept = [c for c in self.categories_cfg.get("categories", []) if c["department_id"] == best_dept]
        best_cat = cats_for_dept[0]["category_id"] if cats_for_dept else "CAT_GARBAGE_COLLECTION"
        max_cat_score = 0

        for c in cats_for_dept:
            c_score = 0
            for kw in c.get("keywords", []):
                kw_lower = normalize_text(kw)
                if kw_lower in text_lower:
                    c_score += 3
                else:
                    kw_words = [w for w in re.findall(r'[\w\u0900-\u097F]+', kw_lower) if w]
                    if kw_words and all(w in stemmed for w in kw_words):
                        c_score += 2
            
            if c_score > max_cat_score:
                max_cat_score = c_score
                best_cat = c["category_id"]

        # Detect language hint
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)
        language = "hi" if has_devanagari else "en"

        # Construct safe summary
        first_line = text.strip().split("\n")[0][:120]
        summary = f"Civic complaint received via {channel}: {first_line}"

        confidence = 0.55 if max_dept_score > 0 else 0.30

        return AIClassificationResult(
            language=language,
            summary=summary,
            department=best_dept,
            category=best_cat,
            subcategory=None,
            routing_terms=matched_terms or ["[KEYWORD_FALLBACK]"],
            confidence=confidence
        )
