"""
Deterministic Urgency Engine for NagarSetu
Calculates transparent urgency component scores (Public Safety, Service Outage, Duration)
and enforces mandatory deterministic safety hazard overrides from config/urgency_rules.json.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple

from app.core.config import settings
from app.schemas.complaint import UrgencyLevel
from app.schemas.triage import UrgencyEvaluationResult, AIClassificationResult

logger = logging.getLogger("nagarsetu.urgency_engine")


class UrgencyEngine:
    """
    Transparent urgency evaluator producing auditable score breakdowns (0-100)
    and enforcing non-negotiable public safety hazard overrides.
    """

    def __init__(self):
        self.urgency_rules_cfg = self._load_rules_config()
        self.rules: List[dict] = self.urgency_rules_cfg.get("rules", [])

    def _load_rules_config(self) -> dict:
        rules_path = settings.CONFIG_DIR / "urgency_rules.json"
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate(
        self,
        complaint_text: str,
        category_id: Optional[str] = None,
        ai_classification: Optional[AIClassificationResult] = None
    ) -> UrgencyEvaluationResult:
        """
        Computes safety, outage, and duration scores, checks for deterministic
        safety overrides, and returns an auditable UrgencyEvaluationResult.
        """
        text_lower = (complaint_text or "").lower()
        evidence_terms: List[str] = []

        # 1. Evaluate Duration Score (0 to 30)
        duration_score, duration_terms = self._compute_duration_score(text_lower)
        evidence_terms.extend(duration_terms)

        # 2. Evaluate Service Outage Score (0 to 30)
        outage_score, outage_terms = self._compute_outage_score(text_lower)
        evidence_terms.extend(outage_terms)

        # 3. Evaluate Public Safety Score (0 to 40)
        safety_score, safety_terms = self._compute_safety_score(text_lower, category_id)
        evidence_terms.extend(safety_terms)

        # 4. Total Operational Score (0 to 100)
        total_operational_score = safety_score + outage_score + duration_score

        # Map to Urgency Level
        if total_operational_score >= 90:
            urgency = UrgencyLevel.CRITICAL
        elif total_operational_score >= 70:
            urgency = UrgencyLevel.HIGH
        elif total_operational_score >= 40:
            urgency = UrgencyLevel.MEDIUM
        else:
            urgency = UrgencyLevel.LOW

        normalized_score = round(total_operational_score / 100.0, 2)
        urgency_reason = (
            f"Evaluated priority score {total_operational_score}/100 "
            f"(Safety: {safety_score}/40, Outage: {outage_score}/30, Duration: {duration_score}/30)."
        )

        # 5. Check Deterministic Safety Overrides (AGENTS.md Rule 2.4)
        override_applied, override_rule = self._check_mandatory_safety_overrides(
            text_lower, category_id
        )

        if override_applied and override_rule:
            enforced_level_str = override_rule.get("enforced_urgency", "CRITICAL")
            enforced_level = UrgencyLevel(enforced_level_str)
            enforced_score = override_rule.get("urgency_score", 0.95)

            # AI or standard rules cannot downgrade a mandatory safety override
            urgency = enforced_level
            normalized_score = max(normalized_score, enforced_score)
            safety_score = max(safety_score, 38)
            urgency_reason = (
                f"[MANDATORY SAFETY OVERRIDE: {override_rule['rule_id']}] "
                f"{override_rule.get('urgency_reason', 'Public safety emergency.')}"
            )
            override_keywords = override_rule.get("conditions", {}).get("keywords", [])
            matched_kws = [kw for kw in override_keywords if kw in text_lower]
            evidence_terms.extend(matched_kws)

            return UrgencyEvaluationResult(
                urgency=urgency,
                urgency_score=normalized_score,
                safety_score=safety_score,
                outage_score=outage_score,
                duration_score=duration_score,
                urgency_reason=urgency_reason,
                urgency_evidence=list(dict.fromkeys(evidence_terms)),
                safety_override_applied=True,
                safety_override_rule_id=override_rule.get("rule_id")
            )

        return UrgencyEvaluationResult(
            urgency=urgency,
            urgency_score=normalized_score,
            safety_score=safety_score,
            outage_score=outage_score,
            duration_score=duration_score,
            urgency_reason=urgency_reason,
            urgency_evidence=list(dict.fromkeys(evidence_terms)),
            safety_override_applied=False,
            safety_override_rule_id=None
        )

    def _compute_duration_score(self, text: str) -> Tuple[int, List[str]]:
        """Parses duration cues in English, Hindi, and Hinglish (0-30)."""
        terms = []

        # Extreme duration (25-30)
        if re.search(r"(months?|mahine|\b(15|20|30)\s*(days|din)|weeks?\s*together|kai\s*hafte)", text):
            terms.append("prolonged duration (>2 weeks)")
            return 28, terms

        # High duration 3-7 days (17-24)
        match_days = re.search(r"\b([3-9]|1[0-4])\s*(days?|din)\b", text)
        if match_days:
            days = int(match_days.group(1))
            terms.append(f"{days} days duration")
            return min(24, 15 + days), terms

        if any(phrase in text for phrase in ["ek hafta", "one week", "1 week", "several days", "kai din"]):
            terms.append("approx 1 week duration")
            return 20, terms

        # Moderate duration 1-2 days (8-16)
        if any(phrase in text for phrase in ["2 days", "2 din", "do din", "since yesterday", "kal se"]):
            terms.append("1-2 days duration")
            return 14, terms

        # Short or unspecified duration (0-7)
        if any(phrase in text for phrase in ["today", "aaj", "few hours", "kuch ghante", "just now"]):
            terms.append("recent occurrence (<24h)")
            return 6, terms

        return 4, terms

    def _compute_outage_score(self, text: str) -> Tuple[int, List[str]]:
        """Assesses service outage scale and population impact (0-30)."""
        terms = []

        # Area-wide / entire colony impact (22-30)
        area_keywords = [
            "entire colony", "whole area", "poori colony", "pure mohalle", "all houses",
            "complete blackout", "no water in entire", "main road blocked", "thoroughfare blocked",
            "ambulance stuck", "pura sector", "low pressure", "low water pressure"
        ]
        matched_area = [kw for kw in area_keywords if kw in text]
        if matched_area:
            terms.extend(matched_area)
            return 26, terms

        # Moderate service disruption (12-21)
        disruption_keywords = [
            "no water", "paani nahi", "light band", "streetlight off", "dark road",
            "ganda paani", "dirty water", "sewer overflow", "naali jaam",
            "water supply stopped", "drain blocked", "blocked drain", "waterlogging",
            "water logging", "drainage chocked", "tree fallen", "fallen tree",
            "blocking access", "driveway blocked", "pothole", "gaddha", "crater"
        ]
        matched_disruption = [kw for kw in disruption_keywords if kw in text]
        if matched_disruption:
            terms.extend(matched_disruption)
            return 18, terms

        # Minor / isolated disruption (0-11)
        return 5, terms

    def _compute_safety_score(self, text: str, category_id: Optional[str]) -> Tuple[int, List[str]]:
        """Assesses public safety, physical hazard, and epidemic risks (0-40)."""
        terms = []

        # High acute danger (32-40)
        acute_keywords = [
            "sparking", "exposed wire", "live wire", "live electrical wire", "exposed live", "exposed electrical wire", "electric shock", "transformer spark",
            "open manhole", "missing manhole", "deep crater", "cave in", "sinkhole",
            "two-wheelers skidded", "accident", "child fell", "bacha gir", "typhoid", "dengue outbreak",
            "snapped wire"
        ]
        matched_acute = [kw for kw in acute_keywords if kw in text]
        if matched_acute:
            terms.extend(matched_acute)
            return 36, terms

        # Moderate hazard (18-31)
        moderate_keywords = [
            "dark street", "dangerous", "skid", "foul smell", "stray dog bite",
            "stray dogs", "dead animal", "carcass", "contaminated water", "yellow water",
            "pothole", "gaddha", "school", "hospital", "tree fallen", "fallen tree",
            "branch fallen", "waterlogging", "water logging", "mosquito", "blocked drain"
        ]
        matched_mod = [kw for kw in moderate_keywords if kw in text]
        if matched_mod:
            terms.extend(matched_mod)
            return 22, terms

        # Low risk / routine sanitation (0-17)
        routine_keywords = ["kachra", "garbage", "sweeping", "dry waste", "paper", "leaves"]
        matched_routine = [kw for kw in routine_keywords if kw in text]
        if matched_routine:
            terms.extend(matched_routine)
            return 8, terms

        return 10, terms

    def _check_mandatory_safety_overrides(
        self,
        text: str,
        category_id: Optional[str]
    ) -> Tuple[bool, Optional[dict]]:
        """
        Checks config/urgency_rules.json for mandatory public safety overrides.
        Returns (True, rule_dict) if a mandatory override condition is satisfied.
        """
        for rule in self.rules:
            if not rule.get("mandatory_override", False):
                continue

            cond = rule.get("conditions", {})
            keywords = cond.get("keywords", [])
            cat_matches = cond.get("category_matches", [])

            # Keyword match check
            keyword_matched = any(kw.lower() in text for kw in keywords)

            # Category match check (optional, true if matched or if not strictly constrained)
            category_matched = (
                category_id in cat_matches if (category_id and cat_matches) else False
            )

            # If strong keyword matches for critical life hazard, trigger override
            if keyword_matched:
                return True, rule

        return False, None
