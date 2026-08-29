from __future__ import annotations

import json

from nightdesk import config
from nightdesk.facts import facts_from_case
from nightdesk.models import CaseRecord, Rails
from nightdesk.policy import stamp_note
from nightdesk.store import store

# Fail-closed rails: first-open receipts without calling Vertex.
_SEED_RAILS = Rails(gemini=False, vertex=False, pubsub=False, use_vertex=True)


def load_sample_cases() -> list[CaseRecord]:
    raw = json.loads(config.SAMPLE_CASES.read_text())
    return [CaseRecord.model_validate(row) for row in raw]


def _stamp_hold_receipt(case: CaseRecord) -> CaseRecord:
    case.shift_id = None
    case.agent_recommended = None
    case.policy_override = False
    return stamp_note(case, facts_from_case(case), rails=_SEED_RAILS)


def seed_hold_receipts() -> list[CaseRecord]:
    """Stamp why + present/missing on every sample case. No Vertex."""
    cases = [_stamp_hold_receipt(c) for c in load_sample_cases()]
    store.replace_cases(cases)
    return cases


def stamp_missing_receipts(cases: list[CaseRecord]) -> list[CaseRecord]:
    """Fill blank notes with fail-closed HOLD receipts. Leaves stamped rows alone."""
    out: list[CaseRecord] = []
    for case in cases:
        if case.note is None:
            _stamp_hold_receipt(case)
        out.append(case)
        store.upsert_case(case)
    return out


def ensure_seeded() -> list[CaseRecord]:
    existing = store.list_cases()
    if not existing:
        return seed_hold_receipts()
    if any(c.note is None for c in existing):
        return stamp_missing_receipts(existing)
    return existing


def reset_queue() -> list[CaseRecord]:
    return seed_hold_receipts()
