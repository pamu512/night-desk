from __future__ import annotations

import json

from nightdesk import config
from nightdesk.models import CaseRecord
from nightdesk.store import store


def load_sample_cases() -> list[CaseRecord]:
    raw = json.loads(config.SAMPLE_CASES.read_text())
    return [CaseRecord.model_validate(row) for row in raw]


def reset_queue() -> list[CaseRecord]:
    cases = load_sample_cases()
    for case in cases:
        case.status = "open"
        case.note = None
        case.agent_recommended = None
        case.final_disposition = None
        case.policy_override = False
        case.shift_id = None
        case.resolved_by = None
        case.resolved_at = None
    store.replace_cases(cases)
    return cases
