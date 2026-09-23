"""
Multi-Signal Similarity Engine for NagarSetu Duplicate & Incident Cluster Detection.
Evaluates 7 weighted signals across English, Hindi (Devanagari), and Hinglish:
1. Semantic / Multilingual Text Similarity
2. Category Similarity
3. Normalized Locality Similarity
4. Ward Similarity
5. Temporal Proximity
6. Department Similarity
7. Extracted Key Terms Similarity
"""

import json
import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Set, Tuple

logger = logging.getLogger("nagarsetu.similarity_engine")

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "clustering_rules.json"


def _normalize_text(text: str) -> str:
    """Normalizes text for comparison by lowering case and stripping punctuation."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> Set[str]:
    """Extracts tokens of 2+ characters."""
    norm = _normalize_text(text)
    return {w for w in norm.split() if len(w) >= 2}


class BaseEmbeddingProvider:
    """Clean abstraction for semantic embeddings."""
    def get_similarity(self, text1: str, text2: str) -> float:
        raise NotImplementedError


class ConceptAndTokenEmbeddingProvider(BaseEmbeddingProvider):
    """
    Lightweight, reliable multilingual similarity provider.
    Maps Hindi, Hinglish, and English civic terms to canonical incident concepts
    and computes weighted concept and token overlap without requiring external APIs.
    """
    def __init__(self, concepts_dict: Dict[str, list]):
        self.concepts_dict = concepts_dict

    def extract_concepts(self, text: str) -> Set[str]:
        text_lower = _normalize_text(text)
        found = set()
        for concept, keywords in self.concepts_dict.items():
            for kw in keywords:
                kw_norm = _normalize_text(kw)
                # Word boundary check for latin or direct substring for Devanagari
                if re.search(r"(?:\b|_)" + re.escape(kw_norm) + r"(?:\b|_)", text_lower) or kw_norm in text_lower:
                    found.add(concept)
                    break
        return found

    def get_similarity(self, text1: str, text2: str) -> float:
        c1 = self.extract_concepts(text1)
        c2 = self.extract_concepts(text2)
        tokens1 = _tokenize(text1)
        tokens2 = _tokenize(text2)

        # Concept Jaccard
        if c1 or c2:
            concept_sim = len(c1 & c2) / float(len(c1 | c2)) if (c1 | c2) else 0.0
        else:
            concept_sim = 0.0

        # Token Jaccard
        token_sim = len(tokens1 & tokens2) / float(len(tokens1 | tokens2)) if (tokens1 | tokens2) else 0.0

        if c1 and c2 and (c1 & c2):
            # Strong concept match: weight concept heavily
            return min(1.0, 0.70 * concept_sim + 0.30 * token_sim + 0.15)
        elif (c1 or c2) and not (c1 & c2):
            # Divergent concepts detected (e.g., pothole vs streetlight): penalize
            return max(0.0, 0.20 * token_sim)
        else:
            # No specific civic concept matched, fall back to pure token overlap
            return token_sim


class SimilarityEngine:
    """
    Computes pairwise similarity scores across 7 weighted signals.
    """

    def __init__(self, config_file: Optional[Path] = None, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        cfg_path = config_file or CONFIG_PATH
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "weights": {
                    "semantic_text": 0.25,
                    "category": 0.15,
                    "canonical_locality": 0.20,
                    "ward": 0.15,
                    "temporal": 0.10,
                    "department": 0.05,
                    "key_terms": 0.10
                },
                "thresholds": {
                    "likely_duplicate": 0.72,
                    "related_incident": 0.48
                },
                "temporal_window_hours": 72.0,
                "multilingual_civic_concepts": {}
            }

        self.weights = self.config.get("weights", {})
        self.thresholds = self.config.get("thresholds", {"likely_duplicate": 0.72, "related_incident": 0.48})
        self.temporal_window = float(self.config.get("temporal_window_hours", 72.0))
        concepts = self.config.get("multilingual_civic_concepts", {})
        self.embedding_provider = embedding_provider or ConceptAndTokenEmbeddingProvider(concepts)

    def compute_similarity(
        self,
        c1: Dict[str, Any],
        c2: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float], str]:
        """
        Computes composite similarity score and returns:
        (composite_score, signal_breakdown, relationship_type)

        Expected dict keys for c1 and c2:
        - complaint_id: str
        - text: str
        - department: Optional[str]
        - category: Optional[str]
        - normalized_locality: Optional[str]
        - ward: Optional[str]
        - zone: Optional[str]
        - timestamp: Optional[datetime]
        - routing_terms: Optional[list]
        """
        # 1. Department Similarity
        dept1 = (c1.get("department") or "").strip()
        dept2 = (c2.get("department") or "").strip()
        if dept1 and dept2:
            s_dept = 1.0 if dept1 == dept2 else 0.0
        else:
            s_dept = 0.5

        # 2. Category Similarity
        cat1 = (c1.get("category") or "").strip()
        cat2 = (c2.get("category") or "").strip()
        if cat1 and cat2:
            if cat1 == cat2:
                s_cat = 1.0
            elif dept1 and dept2 and dept1 == dept2:
                s_cat = 0.40
            else:
                s_cat = 0.0
        else:
            s_cat = 0.40

        # 3. Normalized Locality Similarity
        loc1 = _normalize_text(c1.get("normalized_locality") or "")
        loc2 = _normalize_text(c2.get("normalized_locality") or "")
        if loc1 and loc2 and loc1 != "unknown" and loc2 != "unknown":
            if loc1 == loc2:
                s_loc = 1.0
            elif loc1 in loc2 or loc2 in loc1:
                s_loc = 0.85
            else:
                # Token overlap in locality string (e.g. 'mp nagar zone 1' vs 'mp nagar')
                t_loc1 = _tokenize(loc1)
                t_loc2 = _tokenize(loc2)
                s_loc = len(t_loc1 & t_loc2) / float(len(t_loc1 | t_loc2)) if (t_loc1 | t_loc2) else 0.0
        else:
            s_loc = 0.25  # Neutral default when location unknown

        # 4. Ward Similarity
        w1 = (c1.get("ward") or "").strip()
        w2 = (c2.get("ward") or "").strip()
        z1 = (c1.get("zone") or "").strip()
        z2 = (c2.get("zone") or "").strip()
        if w1 and w2 and w1.lower() != "unknown" and w2.lower() != "unknown":
            if w1.lower() == w2.lower():
                s_ward = 1.0
            elif z1 and z2 and z1.lower() == z2.lower():
                s_ward = 0.35  # Same zone, different ward
            else:
                s_ward = 0.0
        else:
            s_ward = 0.25

        # 5. Temporal Proximity
        t1 = c1.get("timestamp")
        t2 = c2.get("timestamp")
        if t1 and t2 and isinstance(t1, datetime) and isinstance(t2, datetime):
            delta_hours = abs((t1 - t2).total_seconds()) / 3600.0
            if delta_hours <= self.temporal_window:
                s_time = max(0.0, 1.0 - (delta_hours / self.temporal_window))
            else:
                # Decays towards zero past the temporal window
                s_time = max(0.0, math.exp(- (delta_hours - self.temporal_window) / 48.0) * 0.10)
        else:
            s_time = 0.50

        # 6. Extracted Key Terms Similarity
        terms1 = set(c1.get("routing_terms") or [])
        terms2 = set(c2.get("routing_terms") or [])
        if terms1 or terms2:
            s_terms = len(terms1 & terms2) / float(len(terms1 | terms2)) if (terms1 | terms2) else 0.0
        else:
            s_terms = 0.30

        # 7. Semantic / Multilingual Text Similarity
        text1 = c1.get("text") or c1.get("summary") or ""
        text2 = c2.get("text") or c2.get("summary") or ""
        s_text = self.embedding_provider.get_similarity(text1, text2)

        signals = {
            "semantic_text": round(s_text, 4),
            "category": round(s_cat, 4),
            "canonical_locality": round(s_loc, 4),
            "ward": round(s_ward, 4),
            "temporal": round(s_time, 4),
            "department": round(s_dept, 4),
            "key_terms": round(s_terms, 4)
        }

        # Weighted aggregate
        composite = (
            self.weights.get("semantic_text", 0.25) * s_text +
            self.weights.get("category", 0.15) * s_cat +
            self.weights.get("canonical_locality", 0.20) * s_loc +
            self.weights.get("ward", 0.15) * s_ward +
            self.weights.get("temporal", 0.10) * s_time +
            self.weights.get("department", 0.05) * s_dept +
            self.weights.get("key_terms", 0.10) * s_terms
        )

        # SANITY CHECKS & FALSE POSITIVE PREVENTION RULES:
        # Rule A: Different departments cannot be duplicates (e.g. Streetlight vs Park Swings)
        if dept1 and dept2 and dept1 != dept2:
            composite = min(composite, 0.35)

        # Rule B: Different verified wards cannot be duplicate hyper-local incidents
        if w1 and w2 and w1.lower() != "unknown" and w2.lower() != "unknown" and w1.lower() != w2.lower():
            composite = min(composite, 0.45)

        # Rule C: Completely different categories with zero concept overlap
        if cat1 and cat2 and cat1 != cat2 and s_text < 0.20:
            composite = min(composite, 0.40)

        # Rule D: Temporal separation decay past the operational window (e.g. 72h)
        if t1 and t2 and isinstance(t1, datetime) and isinstance(t2, datetime):
            delta_hours = abs((t1 - t2).total_seconds()) / 3600.0
            if delta_hours > self.temporal_window:
                excess_days = (delta_hours - self.temporal_window) / 24.0
                temporal_factor = math.exp(- excess_days / 7.0)
                composite = composite * (0.35 + 0.65 * temporal_factor)

        composite = round(min(1.0, max(0.0, composite)), 4)

        # Classify relationship
        th_dup = self.thresholds.get("likely_duplicate", 0.72)
        th_rel = self.thresholds.get("related_incident", 0.48)

        if composite >= th_dup:
            rel_type = "LIKELY_DUPLICATE"
        elif composite >= th_rel:
            rel_type = "RELATED_INCIDENT"
        else:
            rel_type = "NO_MATCH"

        return composite, signals, rel_type
