"""
Locality Normalizer for NagarSetu
Resolves informal address strings, text mentions, and landmarks to official
canonical municipal localities, wards, and zones using the gazetteer index.
"""

import json
import logging
import re
from typing import Optional, Tuple, Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings
from app.models.gazetteer import LocalityGazetteer, LocalityAlias
from app.schemas.triage import LocalityNormalizationResult

logger = logging.getLogger("nagarsetu.locality_normalizer")


class LocalityNormalizer:
    """
    Deterministic gazetteer resolution engine.
    Ensures zero hallucination: marks unresolvable locations as UNKNOWN.
    """

    def __init__(self):
        self.gazetteer_json = self._load_gazetteer_json()

    def _load_gazetteer_json(self) -> dict:
        gazetteer_path = settings.GAZETTEER_PATH
        if gazetteer_path.exists():
            with open(gazetteer_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def normalize(
        self,
        source_location_hint: Optional[str] = None,
        complaint_text: str = "",
        ai_extracted_locality: Optional[str] = None,
        db: Optional[Session] = None
    ) -> LocalityNormalizationResult:
        """
        Attempts to resolve location against the gazetteer database and JSON index.
        Returns LocalityNormalizationResult with match_type and confidence.
        """
        # Combine candidate location hints
        candidates: List[str] = []
        if source_location_hint and source_location_hint.strip():
            candidates.append(source_location_hint.strip())
        if ai_extracted_locality and ai_extracted_locality.strip():
            candidates.append(ai_extracted_locality.strip())

        # Also search for candidate tokens within complaint text
        text_lower = (complaint_text or "").lower()

        # Step 1: Database Lookup via Aliases and Canonical Localities
        if db:
            result = self._match_against_database(candidates, text_lower, db)
            if result:
                return result

        # Step 2: In-Memory JSON Lookup (Fallback when DB is empty or during offline parsing)
        result = self._match_against_json(candidates, text_lower)
        if result:
            return result

        # Step 3: Anti-Hallucination Fallback (Rule 2.6)
        logger.info("Locality could not be resolved against gazetteer. Marking UNKNOWN.")
        return LocalityNormalizationResult(
            canonical_locality="UNKNOWN",
            ward=None,
            zone=None,
            match_type="none",
            confidence=0.0
        )

    def _clean_token(self, text: str) -> str:
        """Lowercases and cleans token of punctuation for alias lookup."""
        return re.sub(r"[^\w\s]", " ", text).lower().strip()

    def _match_against_database(
        self,
        candidates: List[str],
        text_lower: str,
        db: Session
    ) -> Optional[LocalityNormalizationResult]:
        """Queries LocalityAlias and LocalityGazetteer tables."""
        # 1. Direct candidate alias search
        for cand in candidates:
            cleaned = self._clean_token(cand)
            if not cleaned:
                continue

            # Exact alias lookup
            alias_match = db.query(LocalityAlias).filter(
                LocalityAlias.alias_normalized == cleaned
            ).first()

            if alias_match:
                rec = db.query(LocalityGazetteer).filter(
                    LocalityGazetteer.id == alias_match.gazetteer_id
                ).first()
                if rec:
                    return LocalityNormalizationResult(
                        canonical_locality=rec.canonical_locality,
                        ward=rec.ward,
                        zone=rec.zone,
                        match_type="alias_match",
                        confidence=1.0
                    )

            # Direct canonical name match
            canonical_match = db.query(LocalityGazetteer).filter(
                func.lower(LocalityGazetteer.canonical_locality) == cleaned
            ).first()

            if canonical_match:
                return LocalityNormalizationResult(
                    canonical_locality=canonical_match.canonical_locality,
                    ward=canonical_match.ward,
                    zone=canonical_match.zone,
                    match_type="exact_canonical",
                    confidence=1.0
                )

        # 2. Text substring alias search across all known aliases in DB
        all_aliases = db.query(LocalityAlias).all()
        # Sort by length descending to match longest specific alias first
        all_aliases.sort(key=lambda a: len(a.alias_normalized), reverse=True)

        for alias in all_aliases:
            pattern = rf"\b{re.escape(alias.alias_normalized)}\b"
            if re.search(pattern, text_lower):
                rec = db.query(LocalityGazetteer).filter(
                    LocalityGazetteer.id == alias.gazetteer_id
                ).first()
                if rec:
                    return LocalityNormalizationResult(
                        canonical_locality=rec.canonical_locality,
                        ward=rec.ward,
                        zone=rec.zone,
                        match_type="alias_match",
                        confidence=0.95
                    )

        # 3. Landmark search across DB records
        all_gaz = db.query(LocalityGazetteer).all()
        for g in all_gaz:
            if not g.landmarks:
                continue
            for lm in g.landmarks:
                lm_name = lm.get("name", "").lower()
                if lm_name and re.search(rf"\b{re.escape(lm_name)}\b", text_lower):
                    return LocalityNormalizationResult(
                        canonical_locality=g.canonical_locality,
                        ward=g.ward,
                        zone=g.zone,
                        match_type="landmark_match",
                        confidence=0.88
                    )

        return None

    def _match_against_json(
        self,
        candidates: List[str],
        text_lower: str
    ) -> Optional[LocalityNormalizationResult]:
        """Matches against sample_wards_gazetteer.json structure."""
        zones = self.gazetteer_json.get("zones", [])

        # Check all candidates and text against zones/wards/aliases
        for zone_item in zones:
            zone_name = zone_item.get("zone_name")
            for ward_item in zone_item.get("wards", []):
                ward_name = ward_item.get("ward_name")
                ward_id = ward_item.get("ward_id")
                ward_aliases = [a.lower() for a in ward_item.get("aliases", [])]
                localities = [l.lower() for l in ward_item.get("localities", [])]
                landmarks = ward_item.get("critical_landmarks", [])

                # Check aliases
                for a in ward_aliases + localities:
                    # Match against candidate hints
                    for cand in candidates:
                        if self._clean_token(cand) == a:
                            return LocalityNormalizationResult(
                                canonical_locality=ward_name,
                                ward=f"Ward {ward_item.get('ward_number', ward_id)}",
                                zone=zone_name,
                                match_type="alias_match",
                                confidence=0.95
                            )

                    # Match as substring in text
                    if re.search(rf"\b{re.escape(a)}\b", text_lower):
                        return LocalityNormalizationResult(
                            canonical_locality=ward_name,
                            ward=f"Ward {ward_item.get('ward_number', ward_id)}",
                            zone=zone_name,
                            match_type="alias_match",
                            confidence=0.92
                        )

                # Check landmarks
                for lm in landmarks:
                    lm_name = lm.get("name", "").lower()
                    if lm_name and re.search(rf"\b{re.escape(lm_name)}\b", text_lower):
                        return LocalityNormalizationResult(
                            canonical_locality=ward_name,
                            ward=f"Ward {ward_item.get('ward_number', ward_id)}",
                            zone=zone_name,
                            match_type="landmark_match",
                            confidence=0.88
                        )

        return None
