from __future__ import annotations

from nightdesk.agent import tools
from nightdesk.events import bus
from nightdesk.models import CaseRecord
from nightdesk.runtime import current_case_id
from nightdesk.store import store


def investigate_case(case_id: str, shift_id: str) -> CaseRecord:
    """Gather context with the same tools. Gemini is the only writer; stamp happens after."""
    current_case_id.set(case_id)
    bus.emit(
        shift_id,
        agent="planner",
        kind="plan",
        case_id=case_id,
        message=(
            f"Plan {case_id}: claim → case file → account → device graph → "
            "velocity → loyalty → delivery/travel"
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
    return case
