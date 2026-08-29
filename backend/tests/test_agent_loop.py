import pytest

from nightdesk.agent.shift import run_shift
from nightdesk.policy import CLOSED
from nightdesk.seed import reset_queue
from nightdesk.store import store


@pytest.mark.asyncio
async def test_shift_stamps_holds_when_rails_are_down() -> None:
    reset_queue()
    shift = await run_shift(
        "Stamp a hold receipt on every case. Never close money.",
        force_mock=True,
    )
    assert shift.status == "completed"
    assert shift.counts["processed"] == 10
    assert shift.counts["hold"] == 10
    assert shift.counts.get("escalated", 0) == 0
    assert "auto_closed" not in shift.counts
    assert shift.rails is not None
    assert "gemini" in shift.rails.missing or "pubsub" in shift.rails.missing

    cases = store.list_cases()
    assert len(cases) == 10
    ids = {c.id for c in cases}
    assert "CASE-2404" in ids
    for case in cases:
        assert case.final_disposition == "HOLD"
        assert case.final_disposition not in CLOSED
        assert case.status == "hold"
        assert case.note is not None
        assert case.note.summary.startswith("HOLD:")
        assert case.note.recommended == "HOLD"
        assert case.note.why_human
        assert case.note.missing
        assert "Fail-closed" in case.note.why_human


@pytest.mark.asyncio
async def test_second_shift_does_not_drop_holds() -> None:
    reset_queue()
    await run_shift("first", force_mock=True)
    second = await run_shift("second", force_mock=True)
    assert second.status == "completed"
    assert second.counts["processed"] == 0
    still = store.list_cases()
    assert len(still) == 10
    assert all(c.status == "hold" for c in still)
    assert any(c.id == "CASE-2404" for c in still)
