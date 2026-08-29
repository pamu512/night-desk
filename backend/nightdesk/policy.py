from __future__ import annotations

from nightdesk.models import Disposition, Facts

# Hard floor: the model may recommend, this function is the last word.
# Amounts in USD. Confidence is applied by the caller after this decide().


def decide(facts: Facts) -> tuple[Disposition, str]:
    """Return (disposition, reason). Deterministic. No LLM."""
    if facts.ato_signals:
        return "AUTO_ESCALATE", "Account-takeover markers (reset/email change) plus a refund."
    if facts.card_testing:
        return "AUTO_ESCALATE", "Card-testing burst: many fails across BINs then a micro-ticket."
    if facts.same_device_accounts >= 3 and facts.refund_count_7d >= 3:
        return "AUTO_ESCALATE", "Same-device refund cluster (3+ accounts, 3+ refunds in 7d)."
    if facts.welcome_bonuses >= 3 or (facts.referrals_14d >= 4 and facts.account_age_days < 14):
        return "AUTO_ESCALATE", "Loyalty farm: stacked welcome bonuses or a self-referral loop."
    if facts.inr_with_delivery_proof and facts.amount_usd < 500:
        return "AUTO_ESCALATE", "INR claim contradicted by carrier proof of delivery."
    if facts.same_device_accounts >= 3 and facts.referrals_14d >= 4:
        return "AUTO_ESCALATE", "Referral loop sharing a device fingerprint with a known cluster."

    if facts.household_ambiguous:
        return "HUMAN_QUEUE", "Household loyalty pooling — policy is not encoded, needs an analyst."
    if facts.amount_usd >= 500 and not facts.ato_signals:
        return "HUMAN_QUEUE", "High-value case without a slam-dunk escalate pattern."
    if facts.inr_with_delivery_proof and facts.amount_usd >= 500:
        return "HUMAN_QUEUE", "High-value INR vs delivery proof — confirm before clawback."

    clean_history = facts.prior_fraud_cases == 0 and facts.chargebacks_90d == 0
    if (
        clean_history
        and facts.account_age_days >= 365
        and facts.amount_usd < 250
        and facts.travel_consistent
        and facts.refund_count_7d == 0
    ):
        return "AUTO_CLOSE", "Long-tenured customer, travel matches itinerary, no refund history."

    if (
        clean_history
        and facts.refund_count_7d == 0
        and facts.auth_fails_15m <= 1
        and facts.unique_bins_15m <= 1
        and facts.same_device_accounts <= 1
        and facts.amount_usd < 80
        and facts.welcome_bonuses == 0
        and not facts.ato_signals
    ):
        return "AUTO_CLOSE", "Single-PAN retry after a soft decline; no graph or bonus abuse."

    return "HUMAN_QUEUE", "Mixed or thin evidence — do not auto-act."


def apply_confidence(disposition: Disposition, confidence: float, reason: str) -> tuple[Disposition, str, bool]:
    """Force HUMAN_QUEUE when the writer is unsure. Returns (final, reason, overridden)."""
    if disposition != "HUMAN_QUEUE" and confidence < 0.72:
        return "HUMAN_QUEUE", f"Writer confidence {confidence:.2f} below 0.72 — {reason}", True
    return disposition, reason, False
