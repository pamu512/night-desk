from __future__ import annotations

import logging
import uuid

from nightdesk import config
from nightdesk.agent.mock_loop import investigate_case as mock_investigate
from nightdesk.events import bus
from nightdesk.facts import facts_from_case
from nightdesk.ingest import publish_shift_started
from nightdesk.models import CaseRecord, ShiftRecord, utcnow
from nightdesk.policy import apply_confidence, decide
from nightdesk.runtime import current_case_id, current_shift_id
from nightdesk.store import store

log = logging.getLogger("nightdesk.shift")

STATUS_FOR = {
    "AUTO_CLOSE": "auto_closed",
    "AUTO_ESCALATE": "auto_escalated",
    "HUMAN_QUEUE": "human_queue",
}


def _apply_policy(case: CaseRecord, shift_id: str) -> CaseRecord:
    facts = facts_from_case(case)
    policy_disp, policy_reason = decide(facts)
    confidence = case.note.confidence if case.note else 0.5
    agent_disp = case.agent_recommended or policy_disp
    final, reason, conf_over = apply_confidence(policy_disp, confidence, policy_reason)
    overridden = bool(case.agent_recommended and case.agent_recommended != final) or conf_over
    case.final_disposition = final
    case.policy_override = overridden
    case.status = STATUS_FOR[final]  # type: ignore[assignment]
    case.shift_id = shift_id
    if case.note and final == "HUMAN_QUEUE" and not case.note.why_human:
        case.note.why_human = reason
    store.upsert_case(case)
    bus.emit(
        shift_id,
        agent="policy",
        kind="policy",
        case_id=case.id,
        message=f"{case.id} → {final}" + (" (override)" if overridden else ""),
        data={
            "agent_recommended": agent_disp,
            "policy": policy_disp,
            "final": final,
            "reason": reason,
            "overridden": overridden,
        },
    )
    bus.emit(
        shift_id,
        agent="policy",
        kind="disposition",
        case_id=case.id,
        message=f"{final}: {reason}",
    )
    return case


async def _investigate(case_id: str, shift_id: str, use_gemini: bool) -> CaseRecord:
    if use_gemini:
        from nightdesk.agent.gemini_loop import investigate_case_gemini

        try:
            case = await investigate_case_gemini(case_id, shift_id)
            if case.note is None:
                bus.emit(
                    shift_id,
                    agent="shift_boss",
                    kind="info",
                    case_id=case_id,
                    message="Gemini returned without a note — finishing with the tool planner",
                )
                case = mock_investigate(case_id, shift_id)
            return case
        except Exception as exc:  # noqa: BLE001
            log.exception("Gemini path failed for %s", case_id)
            bus.emit(
                shift_id,
                agent="shift_boss",
                kind="error",
                case_id=case_id,
                message=f"Gemini error ({type(exc).__name__}); falling back to planner",
            )
            return mock_investigate(case_id, shift_id)
    return mock_investigate(case_id, shift_id)


def open_shift(goal: str, *, force_mock: bool = False) -> ShiftRecord:
    shift_id = f"shift-{uuid.uuid4().hex[:10]}"
    use_gemini = config.has_gemini() and not force_mock
    engine = f"adk+{config.GEMINI_MODEL}" if use_gemini else "tool-planner"
    open_cases = store.list_cases(status="open")
    case_ids = [c.id for c in open_cases]
    message_id = publish_shift_started(shift_id, goal, case_ids)
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
    )
    store.upsert_shift(shift)
    return shift


async def run_shift(goal: str, *, force_mock: bool = False, shift: ShiftRecord | None = None) -> ShiftRecord:
    shift = shift or open_shift(goal, force_mock=force_mock)
    shift_id = shift.id
    token = current_shift_id.set(shift_id)
    use_gemini = config.has_gemini() and not force_mock
    engine = shift.engine
    case_ids = list(shift.case_ids)
    bus.emit(
        shift_id,
        agent="shift_boss",
        kind="info",
        message=f"Goal accepted. {len(case_ids)} open cases. Engine={engine}. Store={store.backend}.",
        data={"goal": goal, "case_ids": case_ids},
    )

    try:
        for case_id in case_ids:
            current_case_id.set(case_id)
            case = await _investigate(case_id, shift_id, use_gemini)
            _apply_policy(case, shift_id)

        remaining = store.list_cases(status="open")
        if remaining:
            bus.emit(
                shift_id,
                agent="shift_boss",
                kind="info",
                message=f"{len(remaining)} cases still open — second pass",
            )
            for case in remaining:
                current_case_id.set(case.id)
                done = await _investigate(case.id, shift_id, use_gemini)
                _apply_policy(done, shift_id)

        counts = {
            "auto_closed": len(store.list_cases(status="auto_closed")),
            "auto_escalated": len(store.list_cases(status="auto_escalated")),
            "human_queue": len(store.list_cases(status="human_queue")),
            "open": len(store.list_cases(status="open")),
            "processed": len(case_ids),
        }
        # Counts above are global; restrict to this shift.
        shift_cases = [c for c in store.list_cases() if c.shift_id == shift_id]
        counts = {
            "auto_closed": sum(1 for c in shift_cases if c.status == "auto_closed"),
            "auto_escalated": sum(1 for c in shift_cases if c.status == "auto_escalated"),
            "human_queue": sum(1 for c in shift_cases if c.status == "human_queue"),
            "open": sum(1 for c in shift_cases if c.status == "open"),
            "processed": len(shift_cases),
        }
        shift.status = "completed"
        shift.finished_at = utcnow()
        shift.counts = counts
        store.upsert_shift(shift)
        bus.emit(
            shift_id,
            agent="shift_boss",
            kind="info",
            message=(
                f"Shift complete. auto_close={counts['auto_closed']} "
                f"auto_escalate={counts['auto_escalated']} "
                f"human_queue={counts['human_queue']}"
            ),
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
