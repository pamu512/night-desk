from __future__ import annotations

from typing import Any

from nightdesk.events import bus
from nightdesk.facts import facts_from_case
from nightdesk.models import CaseNote, Disposition
from nightdesk.runtime import current_case_id, current_shift_id
from nightdesk.store import store


def _emit(kind: str, message: str, data: dict | None = None) -> None:
    shift = current_shift_id.get()
    if not shift:
        return
    bus.emit(
        shift,
        agent="investigator",
        kind=kind,  # type: ignore[arg-type]
        message=message,
        case_id=current_case_id.get() or None,
        data=data or {},
    )


def list_open_cases() -> dict[str, Any]:
    """List every OPEN case in the overnight queue with id, title, amount, typology."""
    cases = store.list_cases(status="open")
    _emit("tool", f"list_open_cases → {len(cases)} open", {"count": len(cases)})
    return {
        "count": len(cases),
        "cases": [
            {
                "id": c.id,
                "title": c.title,
                "amount_usd": c.amount_usd,
                "typology": c.typology,
                "rule_hits": c.rule_hits,
            }
            for c in cases
        ],
    }


def get_case(case_id: str) -> dict[str, Any]:
    """Load the full case file: narrative, account, payment, device, rule hits."""
    case = store.get_case(case_id)
    if not case:
        _emit("tool", f"get_case {case_id} → missing")
        return {"status": "error", "message": f"unknown case {case_id}"}
    current_case_id.set(case_id)
    _emit("tool", f"get_case {case_id}", {"title": case.title})
    return {
        "status": "ok",
        "id": case.id,
        "title": case.title,
        "typology": case.typology,
        "amount_usd": case.amount_usd,
        "channel": case.channel,
        "narrative": case.narrative,
        "rule_hits": case.rule_hits,
        "account": case.account,
        "payment": case.payment,
        "device": case.device,
        "refunds_7d": case.refunds_7d,
        "alerted_at": case.alerted_at,
    }


def get_account_profile(account_id: str) -> dict[str, Any]:
    """Account tenure, KYC, lifetime spend, prior fraud, chargebacks."""
    for case in store.list_cases():
        if (case.account or {}).get("id") == account_id:
            _emit("tool", f"get_account_profile {account_id}")
            return {"status": "ok", **case.account}
    _emit("tool", f"get_account_profile {account_id} → missing")
    return {"status": "error", "message": f"unknown account {account_id}"}


def get_device_graph(device_id: str) -> dict[str, Any]:
    """Accounts and cases sharing this device fingerprint — the cheap ring detector."""
    matches = []
    fingerprint = None
    linked: list[str] = []
    for case in store.list_cases():
        dev = case.device or {}
        if dev.get("id") == device_id or device_id in (dev.get("linked_accounts") or []):
            fingerprint = fingerprint or dev.get("fingerprint")
            linked = list({*linked, *(dev.get("linked_accounts") or [])})
            matches.append(
                {
                    "case_id": case.id,
                    "account_id": (case.account or {}).get("id"),
                    "title": case.title,
                    "typology": case.typology,
                }
            )
    _emit(
        "tool",
        f"get_device_graph {device_id} → {len(linked)} linked accounts",
        {"linked": linked, "cases": [m["case_id"] for m in matches]},
    )
    return {
        "status": "ok",
        "device_id": device_id,
        "fingerprint": fingerprint,
        "linked_accounts": linked,
        "related_cases": matches,
        "ring_size": len(linked),
    }


def get_velocity(case_id: str) -> dict[str, Any]:
    """Auth velocity, BIN spray, refund counts for a case."""
    case = store.get_case(case_id)
    if not case:
        return {"status": "error", "message": f"unknown case {case_id}"}
    velocity = case.velocity or {
        "auth_attempts_15m": 1,
        "auth_fails_15m": 0,
        "unique_bins_15m": 1,
        "unique_emails_15m": 1,
    }
    _emit("tool", f"get_velocity {case_id}", velocity)
    return {
        "status": "ok",
        "case_id": case_id,
        **velocity,
        "refund_count_7d": len(case.refunds_7d or []),
        "refunds_7d": case.refunds_7d,
    }


def get_loyalty_history(account_id: str) -> dict[str, Any]:
    """Welcome bonuses, referrals, redemptions — loyalty-farming signals."""
    for case in store.list_cases():
        if (case.account or {}).get("id") == account_id:
            loyalty = case.loyalty or {
                "points_earned_14d": 0,
                "points_redeemed_14d": 0,
                "welcome_bonuses": 0,
                "referrals_14d": 0,
                "redemptions": [],
            }
            _emit("tool", f"get_loyalty_history {account_id}", {"bonuses": loyalty.get("welcome_bonuses")})
            return {"status": "ok", "account_id": account_id, **loyalty}
    return {"status": "error", "message": f"unknown account {account_id}"}


def get_delivery_and_travel(case_id: str) -> dict[str, Any]:
    """Carrier proof-of-delivery, INR labels, travel itinerary, ATO flags, household notes."""
    case = store.get_case(case_id)
    if not case:
        return {"status": "error", "message": f"unknown case {case_id}"}
    payload = {
        "status": "ok",
        "delivery": case.delivery,
        "travel": case.travel,
        "ato": case.ato,
        "household": case.household,
        "network_labels": case.network_labels,
    }
    _emit("tool", f"get_delivery_and_travel {case_id}")
    return payload


def write_case_note(
    case_id: str,
    summary: str,
    typology: str,
    evidence: list[str],
    recommended: str,
    confidence: float,
    why_human: str = "",
) -> dict[str, Any]:
    """Write the structured case note the morning analyst will read. Call once per case."""
    case = store.get_case(case_id)
    if not case:
        return {"status": "error", "message": f"unknown case {case_id}"}
    rec: Disposition
    if recommended not in {"AUTO_CLOSE", "AUTO_ESCALATE", "HUMAN_QUEUE"}:
        recommended = "HUMAN_QUEUE"
    rec = recommended  # type: ignore[assignment]
    note = CaseNote(
        summary=summary.strip(),
        typology=typology,
        evidence=[e for e in evidence if e],
        recommended=rec,
        confidence=max(0.0, min(1.0, float(confidence))),
        why_human=why_human or None,
    )
    case.note = note
    case.agent_recommended = rec
    store.upsert_case(case)
    _emit("note", f"wrote note on {case_id}: {rec}", note.model_dump())
    return {"status": "ok", "case_id": case_id, "recommended": rec}


def mark_case_processing(case_id: str) -> dict[str, Any]:
    """Claim a case so a second worker does not pick it up."""
    case = store.get_case(case_id)
    if not case:
        return {"status": "error", "message": f"unknown case {case_id}"}
    case.status = "processing"
    case.shift_id = current_shift_id.get() or case.shift_id
    store.upsert_case(case)
    current_case_id.set(case_id)
    _emit("tool", f"claimed {case_id}")
    return {"status": "ok", "case_id": case_id}


def inspect_facts(case_id: str) -> dict[str, Any]:
    """Return the policy-normalized fact vector for a case (no recommendation)."""
    case = store.get_case(case_id)
    if not case:
        return {"status": "error", "message": f"unknown case {case_id}"}
    facts = facts_from_case(case)
    _emit("tool", f"inspect_facts {case_id}")
    return {"status": "ok", **facts.model_dump()}


INVESTIGATOR_TOOLS = [
    list_open_cases,
    get_case,
    get_account_profile,
    get_device_graph,
    get_velocity,
    get_loyalty_history,
    get_delivery_and_travel,
    write_case_note,
    mark_case_processing,
    inspect_facts,
]
