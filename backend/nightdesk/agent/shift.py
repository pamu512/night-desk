from __future__ import annotations

import logging
import uuid

from nightdesk import config
from nightdesk.agent.mock_loop import investigate_case as gather_case
from nightdesk.events import bus
from nightdesk.facts import facts_from_case
from nightdesk.ingest import publish_shift_started
from nightdesk.models import CaseRecord, Rails, ShiftRecord, utcnow
from nightdesk.policy import stamp_note
from nightdesk.rails import assess_rails
from nightdesk.runtime import current_case_id, current_shift_id
from nightdesk.store import store

log = logging.getLogger("nightdesk.shift")


def _stamp(case: CaseRecord, shift_id: str, rails: Rails) -> CaseRecord:
    facts = facts_from_case(case)
    draft = case.note
    stamped = stamp_note(case, facts, rails, gemini_draft=draft)
    stamped.shift_id = shift_id
    store.upsert_case(stamped)
    bus.emit(
        shift_id,
        agent="policy",
        kind="policy",
        case_id=stamped.id,
        message=f"{stamped.id} → {stamped.final_disposition}"
        + (" (override)" if stamped.policy_override else ""),
        data={
            "final": stamped.final_disposition,
            "reason": stamped.note.why_human if stamped.note else "",
            "present": stamped.note.present if stamped.note else [],
            "missing": stamped.note.missing if stamped.note else [],
            "overridden": stamped.policy_override,
            "rails_missing": rails.missing,
        },
    )
    bus.emit(
        shift_id,
        agent="policy",
        kind="disposition",
        case_id=stamped.id,
        message=stamped.note.summary if stamped.note else str(stamped.final_disposition),
    )
    return stamped


async def _investigate(
    case_id: str, shift_id: str, use_gemini: bool, rails: Rails
) -> tuple[CaseRecord, Rails]:
    if use_gemini and rails.ok:
        from nightdesk.agent.gemini_loop import investigate_case_gemini

        try:
            return await investigate_case_gemini(case_id, shift_id), rails
        except Exception as exc:  # noqa: BLE001
            log.exception("Gemini path failed for %s", case_id)
            bus.emit(
                shift_id,
                agent="shift_boss",
                kind="error",
                case_id=case_id,
                message=f"Gemini error ({type(exc).__name__}); fail-closed HOLD",
            )
            case = store.get_case(case_id) or gather_case(case_id, shift_id)
            down = rails.model_copy(update={"gemini": False, "vertex": False})
            return case, down
    return gather_case(case_id, shift_id), rails


def open_shift(goal: str, *, force_mock: bool = False) -> ShiftRecord:
    shift_id = f"shift-{uuid.uuid4().hex[:10]}"
    use_gemini = config.has_gemini() and not force_mock
    engine = f"adk+{config.GEMINI_MODEL}" if use_gemini else "receipt-stamp"
    queue = store.list_cases()
    case_ids = [c.id for c in queue]
    message_id = publish_shift_started(shift_id, goal, case_ids)
    rails = assess_rails(pubsub_up=message_id is not None, gemini_up=use_gemini)
    shift = ShiftRecord(
        id=shift_id,
        goal=goal,
        status="running",
        started_at=utcnow(),
        engine=engine,
        model=config.GEMINI_MODEL if use_gemini else "none",
        pubsub_message_id=message_id,
        store_backend=store.backend,
        case_ids=case_ids,
        rails=rails,
    )
    store.upsert_shift(shift)
    return shift


async def run_shift(goal: str, *, force_mock: bool = False, shift: ShiftRecord | None = None) -> ShiftRecord:
    shift = shift or open_shift(goal, force_mock=force_mock)
    shift_id = shift.id
    token = current_shift_id.set(shift_id)
    use_gemini = config.has_gemini() and not force_mock
    rails = shift.rails or assess_rails(
        pubsub_up=shift.pubsub_message_id is not None,
        gemini_up=use_gemini,
    )
    case_ids = list(shift.case_ids)
    bus.emit(
        shift_id,
        agent="shift_boss",
        kind="info",
        message=(
            f"Goal accepted. {len(case_ids)} cases. Engine={shift.engine}. "
            f"Rails present={rails.present or ['—']} missing={rails.missing or ['—']}."
        ),
        data={"goal": goal, "case_ids": case_ids, "rails": rails.model_dump()},
    )

    try:
        for case_id in case_ids:
            current_case_id.set(case_id)
            case, case_rails = await _investigate(case_id, shift_id, use_gemini, rails)
            _stamp(case, shift_id, case_rails)

        shift_cases = [c for c in store.list_cases() if c.shift_id == shift_id]
        counts = {
            "hold": sum(1 for c in shift_cases if c.final_disposition == "HOLD"),
            "escalated": sum(1 for c in shift_cases if c.final_disposition == "ESCALATE"),
            "processed": len(shift_cases),
        }
        shift.status = "completed"
        shift.finished_at = utcnow()
        shift.counts = counts
        shift.rails = rails
        store.upsert_shift(shift)
        bus.emit(
            shift_id,
            agent="shift_boss",
            kind="info",
            message=f"Receipts stamped. hold={counts['hold']} escalate={counts['escalated']}",
            data=counts,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("shift failed")
        shift.status = "failed"
        shift.finished_at = utcnow()
        shift.error = f"{type(exc).__name__}: {exc}"
        store.upsert_shift(shift)
        bus.emit(shift_id, agent="shift_boss", kind="error", message=shift.error)
        raise
    finally:
        bus.close(shift_id)
        current_shift_id.reset(token)
    return shift
