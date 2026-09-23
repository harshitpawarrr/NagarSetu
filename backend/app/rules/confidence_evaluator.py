"""
Confidence Evaluator for NagarSetu
Applies configurable operational thresholds to determine whether a ticket
can proceed along the normal operator review path or requires manual review.
"""

from typing import Optional
from app.core.config import settings
from app.schemas.triage import ReviewFlagsResult


class ConfidenceEvaluator:
    """
    Evaluates classification, routing, and locality confidence against
    system thresholds (Rule 2.4).
    """

    def __init__(self):
        self.threshold_normal = settings.CONFIDENCE_THRESHOLD_NORMAL
        self.threshold_attention = settings.CONFIDENCE_THRESHOLD_ATTENTION

    def evaluate(
        self,
        classification_confidence: float,
        routing_confidence: float,
        locality_confidence: float = 1.0,
        safety_override_applied: bool = False,
        category_valid: bool = True,
        locality_match_type: str = "exact_canonical"
    ) -> ReviewFlagsResult:
        """
        Determines operational review flags and confidence tier.
        """
        min_confidence = min(classification_confidence, routing_confidence)

        # 1. Critical Low Confidence (< 0.50) or Invalid Category
        if min_confidence < self.threshold_attention or not category_valid:
            reasons = []
            if min_confidence < self.threshold_attention:
                reasons.append(f"Low confidence ({min_confidence:.2f} < {self.threshold_attention})")
            if not category_valid:
                reasons.append("Unverified department/category taxonomy match")

            return ReviewFlagsResult(
                requires_manual_review=True,
                review_flagged=True,
                review_reason=f"Manual review required: {', '.join(reasons)}.",
                confidence_tier="MANUAL_REVIEW"
            )

        # 2. Moderate Confidence (0.50 to 0.79) or Unknown Locality
        if min_confidence < self.threshold_normal or locality_match_type == "none":
            reasons = []
            if min_confidence < self.threshold_normal:
                reasons.append(f"Moderate confidence ({min_confidence:.2f})")
            if locality_match_type == "none":
                reasons.append("Locality could not be verified in gazetteer")

            return ReviewFlagsResult(
                requires_manual_review=False,
                review_flagged=True,
                review_reason=f"Flagged for operator attention: {', '.join(reasons)}.",
                confidence_tier="ATTENTION"
            )

        # 3. High Confidence (>= 0.80)
        review_reason = "Standard high-confidence triage recommendation."
        if safety_override_applied:
            review_reason += " (Mandatory safety hazard override active)."

        return ReviewFlagsResult(
            requires_manual_review=False,
            review_flagged=safety_override_applied,
            review_reason=review_reason,
            confidence_tier="NORMAL"
        )
