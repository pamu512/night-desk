import pytest

from nightdesk.agent.shift import run_shift
from nightdesk.seed import reset_queue
from nightdesk.store import store


@pytest.mark.asyncio
async def test_night_shift_drains_queue_and_writes_notes() -> None:
    reset_queue()
    shift = await run_shift(
        "Clear the overnight refund, loyalty, and payment-abuse queue.",
        force_mock=True,
    )
    assert shift.status == "completed"
    assert shift.counts["processed"] == 10
    assert shift.counts["auto_escalated"] == 6
    assert shift.counts["auto_closed"] == 2
    assert shift.counts["human_queue"] == 2
    assert shift.counts["open"] == 0

    inbox = store.list_cases(status="human_queue")
    assert {c.id for c in inbox} == {"CASE-2405", "CASE-2410"}
    for case in inbox:
        assert case.note is not None
        assert case.note.summary
        assert case.note.evidence
        assert case.note.why_human

    closed = store.list_cases(status="auto_closed")
    assert {c.id for c in closed} == {"CASE-2404", "CASE-2408"}
    for case in store.list_cases():
        assert case.note is not None
        assert case.final_disposition is not None
        assert case.status != "open"


@pytest.mark.asyncio
async def test_second_shift_on_empty_queue_is_a_noop() -> None:
    reset_queue()
    await run_shift("first", force_mock=True)
    second = await run_shift("second", force_mock=True)
    assert second.status == "completed"
    assert second.counts["processed"] == 0
    assert second.case_ids == []
