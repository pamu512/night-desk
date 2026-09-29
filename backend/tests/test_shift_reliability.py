import asyncio
import os
from pathlib import Path

import pytest

from nightdesk.agent.shift import open_shift, run_shift
from nightdesk.models import Rails
from nightdesk.seed import reset_queue
from nightdesk.store import store


@pytest.mark.asyncio
async def test_hung_gemini_stream_falls_back_without_hanging_shift(monkeypatch) -> None:
    reset_queue()
    monkeypatch.setenv("NIGHTDESK_GEMINI_TIMEOUT", "0.05")
    monkeypatch.setattr("nightdesk.agent.gemini_loop.build_root_agent", lambda: object())

    class HungRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run_async(self, **kwargs):
            async def _gen():
                await asyncio.sleep(60)
                if False:
                    yield None

            return _gen()

    class FakeSessionService:
        async def create_session(self, **kwargs):
            return None

    class Fake:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("google.adk.runners.Runner", HungRunner)
    monkeypatch.setattr("google.adk.sessions.InMemorySessionService", FakeSessionService)
    monkeypatch.setattr("google.genai.types.Content", Fake)
    monkeypatch.setattr("google.genai.types.Part", Fake)

    from nightdesk.agent.shift import _investigate

    rails = Rails(gemini=True, vertex=True, pubsub=True, use_vertex=True)
    case, down = await asyncio.wait_for(
        _investigate("CASE-2401", "shift-timeout", True, rails),
        timeout=2,
    )
    assert case.id == "CASE-2401"
    assert down.gemini is False
    assert down.vertex is False


@pytest.mark.asyncio
async def test_run_shift_skips_cases_claimed_by_other_live_shift() -> None:
    reset_queue()
    holder = open_shift("holder", force_mock=True)
    claimed_ids = [c.id for c in store.list_cases()[:4]]
    for case_id in claimed_ids:
        claimed = store.claim_case(case_id, holder.id)
        assert claimed is not None
        assert claimed.status == "processing"
        assert claimed.shift_id == holder.id

    other = await run_shift("other", force_mock=True)
    for case_id in claimed_ids:
        case = store.get_case(case_id)
        assert case is not None
        assert case.shift_id == holder.id
        assert case.status == "processing"
    assert other.counts["processed"] == 6
    assert store.claim_case(claimed_ids[0], other.id) is None


@pytest.mark.asyncio
async def test_concurrent_run_shifts_do_not_double_process(monkeypatch) -> None:
    reset_queue()
    from nightdesk.agent import shift as shift_mod

    real = shift_mod._investigate

    async def slow(case_id: str, shift_id: str, use_gemini: bool, rails: Rails):
        await asyncio.sleep(0.02)
        return await real(case_id, shift_id, use_gemini, rails)

    monkeypatch.setattr(shift_mod, "_investigate", slow)
    first, second = await asyncio.gather(
        run_shift("first", force_mock=True),
        run_shift("second", force_mock=True),
    )
    assert first.counts["processed"] + second.counts["processed"] == 10
    owners = {c.shift_id for c in store.list_cases()}
    assert owners <= {first.id, second.id}
    assert None not in owners


def test_save_file_uses_atomic_replace(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    reset_queue()
    assert calls
    assert any(Path(dst).name == "store.json" for _src, dst in calls)
    assert all(Path(src).parent == Path(dst).parent for src, dst in calls)
