"""
Explainable Routing Engine for NagarSetu
Determines department assignment using config/routing_rules.json and official taxonomy.
Generates verifiable evidence, rule IDs, and human-readable explanations at individual ticket level.
"""

import json
import logging
from typing import Optional, Dict, Any, List, Tuple

from app.core.config import settings
from app.schemas.triage import ExplainableRoutingResult, LocalityNormalizationResult

logger = logging.getLogger("nagarsetu.routing_engine")


class RoutingEngine:
    """
    Deterministic explainable routing engine.
    Ensures every routing recommendation carries transparent, auditable evidence.
    """

    def __init__(self):
        self.routing_rules_cfg = self._load_json("routing_rules.json")
        self.departments_cfg = self._load_json("departments.json")
        self.categories_cfg = self._load_json("categories.json")

        self.rules: List[dict] = self.routing_rules_cfg.get("rules", [])
        self.fallback_dept: str = self.routing_rules_cfg.get(
            "default_fallback_department", "DEPT_SWM"
        )
        self.dept_map: Dict[str, dict] = {
            d["department_id"]: d for d in self.departments_cfg.get("departments", [])
        }
        self.cat_to_dept: Dict[str, str] = {
            c["category_id"]: c["department_id"]
            for c in self.categories_cfg.get("categories", [])
        }
        self.cat_map: Dict[str, dict] = {
            c["category_id"]: c for c in self.categories_cfg.get("categories", [])
        }

    def _load_json(self, filename: str) -> dict:
        filepath = settings.CONFIG_DIR / filename
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def route(
        self,
        predicted_department: Optional[str],
        category_id: Optional[str],
        routing_terms: Optional[List[str]] = None,
        complaint_text: str = "",
        locality_info: Optional[LocalityNormalizationResult] = None
    ) -> ExplainableRoutingResult:
        """
        Determines the recommended department, producing evidence and rule citations.
        """
        text_lower = (complaint_text or "").lower()
        terms = [t.lower() for t in (routing_terms or [])]
        combined_text_and_terms = text_lower + " " + " ".join(terms)

        # 1. Deterministic Routing Rules Match (from config/routing_rules.json)
        rule_match = self._match_deterministic_rules(category_id, combined_text_and_terms)
        if rule_match:
            rule, matched_kws = rule_match
            target_dept = rule["target_department"]
            dept_obj = self.dept_map.get(target_dept, {})
            dept_name = dept_obj.get("name", target_dept)

            explanation = rule.get("routing_evidence_template", "").format(
                matched_keywords=", ".join(matched_kws) if matched_kws else "category match",
                category_id=category_id or "General"
            )
            if not explanation:
                explanation = (
                    f"Matched rule {rule['rule_id']} assigning ticket to {dept_name} "
                    f"based on keywords [{', '.join(matched_kws)}]."
                )

            evidence = list(dict.fromkeys(matched_kws + ([category_id] if category_id else [])))

            return ExplainableRoutingResult(
                recommended_department=target_dept,
                routing_confidence=rule.get("base_confidence", 0.90),
                routing_evidence=evidence,
                routing_rule_id=rule["rule_id"],
                routing_explanation=explanation
            )

        # 2. Taxonomy Hierarchy Mapping (Category to Department)
        if category_id and category_id in self.cat_to_dept:
            canonical_dept = self.cat_to_dept[category_id]
            dept_obj = self.dept_map.get(canonical_dept, {})
            dept_name = dept_obj.get("name", canonical_dept)
            cat_obj = self.cat_map.get(category_id, {})
            cat_name = cat_obj.get("name", category_id)

            evidence = list(dict.fromkeys(terms + [category_id]))
            explanation = (
                f"Category '{cat_name}' ({category_id}) maps directly to {dept_name} "
                f"under municipal taxonomy."
            )

            return ExplainableRoutingResult(
                recommended_department=canonical_dept,
                routing_confidence=0.85,
                routing_evidence=evidence,
                routing_rule_id="ROUTE_TAXONOMY_MAP",
                routing_explanation=explanation
            )

        # 3. Direct Valid Department Match (AI fallback)
        if predicted_department and predicted_department in self.dept_map:
            dept_obj = self.dept_map[predicted_department]
            dept_name = dept_obj.get("name", predicted_department)
            evidence = list(dict.fromkeys(terms + [predicted_department]))

            return ExplainableRoutingResult(
                recommended_department=predicted_department,
                routing_confidence=0.75,
                routing_evidence=evidence,
                routing_rule_id="ROUTE_AI_DIRECT",
                routing_explanation=f"Assigned to {dept_name} based on classification synthesis."
            )

        # 4. Unknown / Conflicting Routing Fallback (Rule 2.4 & Rule 2.5)
        fallback_dept_obj = self.dept_map.get(self.fallback_dept, {})
        fallback_name = fallback_dept_obj.get("name", self.fallback_dept)
        logger.warning("No routing rule matched. Routing to fallback department: %s", self.fallback_dept)

        return ExplainableRoutingResult(
            recommended_department=self.fallback_dept,
            routing_confidence=0.30,
            routing_evidence=["[UNKNOWN_CATEGORY_OR_DEPT]"],
            routing_rule_id="ROUTE_UNKNOWN_FALLBACK",
            routing_explanation=(
                f"Unclassified or ambiguous grievance. Assigned to fallback department "
                f"'{fallback_name}' ({self.fallback_dept}) with manual operator review required."
            )
        )

    def _match_deterministic_rules(
        self,
        category_id: Optional[str],
        text: str
    ) -> Optional[Tuple[dict, List[str]]]:
        """Scans rules for matching category prefixes and required keywords."""
        for rule in self.rules:
            cond = rule.get("conditions", {})
            required_kws = cond.get("required_keywords_any", [])
            cat_prefix = cond.get("category_prefix")

            # Check category prefix / match
            cat_matched = False
            if cat_prefix and category_id:
                if category_id.startswith(cat_prefix) or category_id == cat_prefix:
                    cat_matched = True

            # Check keywords
            matched_kws = [kw for kw in required_kws if kw.lower() in text]

            # Rule fires if either category matches and keywords match, or keywords strongly match
            if cat_matched or (len(matched_kws) >= 1):
                return rule, matched_kws

        return None
