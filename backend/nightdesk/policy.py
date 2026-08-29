from __future__ import annotations

from nightdesk.models import CaseNote, CaseRecord, Disposition, Facts, Rails

CLOSED = frozenset({"AUTO_CLOSE", "CLOSE", "auto_closed", "closed"})

_SIGNAL_ORDER = ("device_ring", "bonuses", "fails/BINs", "INR+POD", "ATO")


def _signals(facts: Facts) -> dict[str, str | None]:
    ring = (
        f"device_ring={facts.same_device_accounts}"
        if facts.same_device_accounts >= 3
        else None
    )
    bonuses = None
    if facts.welcome_bonuses >= 3 or facts.referrals_14d >= 4:
        bonuses = f"bonuses={facts.welcome_bonuses}/refs={facts.referrals_14d}"
    fails = None
    if facts.card_testing or facts.auth_fails_15m >= 8:
        fails = f"fails={facts.auth_fails_15m}/BINs={facts.unique_bins_15m}"
    return {
        "device_ring": ring,
        "bonuses": bonuses,
        "fails/BINs": fails,
        "INR+POD": "INR+POD" if facts.inr_with_delivery_proof else None,
        "ATO": "ATO" if facts.ato_signals else None,
    }


def fired_evidence(facts: Facts) -> list[str]:
    """Only the named fire signals. No narrative."""
    sig = _signals(facts)
    return [sig[k] for k in _SIGNAL_ORDER if sig[k]]


def receipt_present_missing(facts: Facts) -> tuple[list[str], list[str]]:
    sig = _signals(facts)
    present = [sig[k] for k in _SIGNAL_ORDER if sig[k]]
    missing = [k for k in _SIGNAL_ORDER if not sig[k]]
    return present, missing


def decide(facts: Facts, rails: Rails | None = None) -> tuple[Disposition, str]:
    """Two-way only: HOLD or ESCALATE. Never close money. Fail-closed on missing rails."""
    if rails is not None and not rails.ok:
        missing = ", ".join(rails.missing)
        return "HOLD", f"Fail-closed: {missing} missing — never silent deny."

    if facts.ato_signals:
        return "ESCALATE", "Account-takeover markers (reset/email change) plus a refund."
    if facts.card_testing:
        return "ESCALATE", "Card-testing burst: many fails across BINs then a micro-ticket."
    if facts.same_device_accounts >= 3 and facts.refund_count_7d >= 3:
        return "ESCALATE", "Same-device refund cluster (3+ accounts, 3+ refunds in 7d)."
    if facts.welcome_bonuses >= 3 or (facts.referrals_14d >= 4 and facts.account_age_days < 14):
        return "ESCALATE", "Loyalty farm: stacked welcome bonuses or a self-referral loop."
    if facts.inr_with_delivery_proof and facts.amount_usd < 500:
        return "ESCALATE", "INR claim contradicted by carrier proof of delivery."
    if facts.same_device_accounts >= 3 and facts.referrals_14d >= 4:
        return "ESCALATE", "Referral loop sharing a device fingerprint with a known cluster."

    if facts.household_ambiguous:
        return "HOLD", "Household loyalty pooling — policy is not encoded."
    if facts.amount_usd >= 500:
        return "HOLD", "High-value case without a slam-dunk escalate pattern."
    if facts.inr_with_delivery_proof:
        return "HOLD", "INR vs delivery proof — confirm before clawback."
    if facts.travel_consistent:
        return "HOLD", "Travel matches itinerary — do not close money unattended."
    return "HOLD", "Thin or mixed evidence — hold. Never close money unattended."


def stamp_note(
    case: CaseRecord,
    facts: Facts,
    rails: Rails | None = None,
    gemini_draft: CaseNote | None = None,
) -> CaseRecord:
    """Overwrite the note from decide(). Gemini may draft; the stamp is the receipt."""
    final, reason = decide(facts, rails)
    present, missing = receipt_present_missing(facts)
    gemini_rec = gemini_draft.recommended if gemini_draft else None
    gemini_summary = gemini_draft.summary if gemini_draft else None
    override = bool(gemini_rec and gemini_rec != final)
    case.note = CaseNote(
        summary=f"{final}: {reason}",
        typology=case.typology,
        evidence=fired_evidence(facts),
        recommended=final,
        why_human=reason,
        present=present,
        missing=missing,
        gemini_summary=gemini_summary,
        gemini_recommended=gemini_rec,
        override=override,
    )
    case.agent_recommended = gemini_rec
    case.final_disposition = final
    case.policy_override = override
    case.status = "hold" if final == "HOLD" else "escalated"
    return case


def coerce_disposition(raw: str) -> Disposition:
    """Map leftover vocabulary onto the two-way lock. Close verbs become HOLD."""
    up = (raw or "").upper().replace("AUTO_", "").replace("HUMAN_QUEUE", "HOLD")
    if up in {"ESCALATE", "ESCALATED"}:
        return "ESCALATE"
    return "HOLD"
