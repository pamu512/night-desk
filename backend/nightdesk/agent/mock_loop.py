from __future__ import annotations

from nightdesk.agent import tools
from nightdesk.events import bus
from nightdesk.facts import facts_from_case
from nightdesk.models import CaseRecord
from nightdesk.policy import decide
from nightdesk.runtime import current_case_id
from nightdesk.store import store


def _note_for(case: CaseRecord) -> tuple[str, list[str], float]:
    facts = facts_from_case(case)
    recommended, reason = decide(facts)
    evidence: list[str] = [
        f"typology={case.typology}",
        f"amount=${case.amount_usd:.2f}",
        f"account_age_days={facts.account_age_days}",
        f"device_ring={facts.same_device_accounts}",
        f"refunds_7d={facts.refund_count_7d}",
    ]
    if facts.ato_signals:
        evidence.append("ATO: password reset and/or email change")
    if facts.card_testing:
        evidence.append(f"auth fails {facts.auth_fails_15m} across {facts.unique_bins_15m} BINs")
    if facts.inr_with_delivery_proof:
        evidence.append("INR reason with carrier proof of delivery")
    if facts.travel_consistent:
        evidence.append("travel itinerary matches geo hop")
    if facts.welcome_bonuses or facts.referrals_14d:
        evidence.append(f"welcome_bonuses={facts.welcome_bonuses} referrals_14d={facts.referrals_14d}")
    if facts.household_ambiguous:
        evidence.append("household point pooling; policy not encoded")
    summary = f"{case.title}. {case.narrative} Policy view: {reason}"
    confidence = 0.91 if recommended != "HUMAN_QUEUE" else 0.64
    if recommended == "HUMAN_QUEUE" and facts.amount_usd >= 500:
        confidence = 0.58
    return summary, evidence, confidence


def investigate_case(case_id: str, shift_id: str) -> CaseRecord:
    """Scripted planner that still calls the real tools — used when Gemini is off."""
    current_case_id.set(case_id)
    bus.emit(
        shift_id,
        agent="planner",
        kind="plan",
        case_id=case_id,
        message=(
            f"Plan {case_id}: claim → case file → account → device graph → "
            "velocity → loyalty → delivery/travel → write note"
        ),
    )
    tools.mark_case_processing(case_id)
    case_blob = tools.get_case(case_id)
    account_id = (case_blob.get("account") or {}).get("id") or ""
    device_id = (case_blob.get("device") or {}).get("id") or ""
    if account_id:
        tools.get_account_profile(account_id)
        tools.get_loyalty_history(account_id)
    if device_id:
        tools.get_device_graph(device_id)
    tools.get_velocity(case_id)
    tools.get_delivery_and_travel(case_id)

    case = store.get_case(case_id)
    if not case:
        raise RuntimeError(f"case vanished: {case_id}")
    summary, evidence, confidence = _note_for(case)
    facts = facts_from_case(case)
    recommended, _reason = decide(facts)
    tools.write_case_note(
        case_id=case_id,
        summary=summary,
        typology=case.typology,
        evidence=evidence,
        recommended=recommended,
        confidence=confidence,
        why_human=_reason if recommended == "HUMAN_QUEUE" else "",
    )
    refreshed = store.get_case(case_id)
    assert refreshed is not None
    return refreshed
