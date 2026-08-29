from __future__ import annotations

from nightdesk.models import CaseRecord, Facts


def facts_from_case(case: CaseRecord) -> Facts:
    device = case.device or {}
    linked = device.get("linked_accounts") or []
    loyalty = case.loyalty or {}
    velocity = case.velocity or {}
    delivery = case.delivery or {}
    travel = case.travel or {}
    ato = case.ato or {}
    household = case.household or {}
    refunds = case.refunds_7d or []
    inr = any(r.get("reason") == "item_not_received" for r in refunds)
    auth_fails = int(velocity.get("auth_fails_15m") or 0)
    unique_bins = int(velocity.get("unique_bins_15m") or 0)
    card_testing = auth_fails >= 8 and unique_bins >= 3
    return Facts(
        case_id=case.id,
        amount_usd=float(case.amount_usd),
        account_age_days=int((case.account or {}).get("age_days") or 0),
        prior_fraud_cases=int((case.account or {}).get("prior_fraud_cases") or 0),
        chargebacks_90d=int((case.account or {}).get("chargebacks_90d") or 0),
        refund_count_7d=len(refunds),
        same_device_accounts=len(linked),
        welcome_bonuses=int(loyalty.get("welcome_bonuses") or 0),
        referrals_14d=int(loyalty.get("referrals_14d") or 0),
        auth_fails_15m=auth_fails,
        unique_bins_15m=unique_bins,
        ato_signals=bool(ato.get("password_reset") or ato.get("email_changed")),
        inr_with_delivery_proof=bool(inr and delivery.get("proof")),
        travel_consistent=bool(travel.get("itinerary_match")),
        household_ambiguous=bool(household) and household.get("policy_allows_pooling") is None,
        card_testing=card_testing,
        typology=case.typology,
    )
