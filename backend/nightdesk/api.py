from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from nightdesk import config
from nightdesk.events import bus
from nightdesk.models import utcnow
from nightdesk.seed import reset_queue
from nightdesk.store import store

log = logging.getLogger("nightdesk.api")
STATIC_DIR = Path(os.getenv("NIGHTDESK_STATIC", config.ROOT / "web" / "out"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if not store.list_cases():
        reset_queue()
        log.info("Seeded sample queue")
    yield


app = FastAPI(title="Night Desk", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_shift_tasks: dict[str, asyncio.Task[None]] = {}


class ShiftRequest(BaseModel):
    goal: str = Field(
        default=(
            "Clear the overnight refund, loyalty, and payment-abuse queue. "
            "Write a case note on every open case. Queue only the real decisions for a human."
        )
    )
    force_mock: bool = False


class ResolveRequest(BaseModel):
    action: str
    note: str = ""


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "nightdesk",
        "gemini": config.has_gemini(),
        "model": config.GEMINI_MODEL,
        "vertex": config.USE_VERTEX,
        "store": store.backend,
        "store_fallback": store.fallback_reason,
        "project": config.GOOGLE_CLOUD_PROJECT,
        "pubsub_topic": config.PUBSUB_TOPIC,
    }


@app.get("/api/cases")
def list_cases(status: str | None = None) -> dict[str, Any]:
    cases = store.list_cases(status=status)
    return {"cases": [c.model_dump() for c in cases]}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    return case.model_dump()


@app.get("/api/inbox")
def inbox() -> dict[str, Any]:
    cases = store.list_cases(status="human_queue")
    return {"cases": [c.model_dump() for c in cases]}


@app.get("/api/shifts")
def list_shifts() -> dict[str, Any]:
    return {"shifts": [s.model_dump() for s in store.list_shifts()]}


@app.get("/api/shifts/{shift_id}")
def get_shift(shift_id: str) -> dict[str, Any]:
    shift = store.get_shift(shift_id)
    if not shift:
        raise HTTPException(404, "shift not found")
    return {
        **shift.model_dump(),
        "events": [e.model_dump() for e in bus.history(shift_id)],
    }


@app.get("/api/shifts/{shift_id}/events")
async def shift_events(shift_id: str) -> StreamingResponse:
    if store.get_shift(shift_id) is None and shift_id not in _shift_tasks:
        raise HTTPException(404, "shift not found")

    async def gen():
        q = bus.subscribe(shift_id)
        try:
            while True:
                event = await q.get()
                if event is None:
                    yield "event: done\ndata: {}\n\n"
                    break
                yield f"data: {json.dumps(event.model_dump())}\n\n"
        finally:
            bus.unsubscribe(shift_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/shifts")
async def start_shift(body: ShiftRequest) -> dict[str, Any]:
    from nightdesk.agent.shift import open_shift, run_shift

    shift = open_shift(body.goal, force_mock=body.force_mock)

    async def _run() -> None:
        try:
            await run_shift(body.goal, force_mock=body.force_mock, shift=shift)
        except Exception:
            log.exception("background shift failed")

    _shift_tasks[shift.id] = asyncio.create_task(_run())
    return shift.model_dump()


@app.post("/api/cases/{case_id}/resolve")
def resolve_case(case_id: str, body: ResolveRequest) -> dict[str, Any]:
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(404, "case not found")
    if body.action not in {"close", "escalate"}:
        raise HTTPException(400, "action must be close or escalate")
    case.status = "resolved"
    case.resolved_by = "analyst"
    case.resolved_at = utcnow()
    if body.note and case.note:
        case.note.summary = f"{case.note.summary}\n\nAnalyst: {body.note}"
    store.upsert_case(case)
    return case.model_dump()


@app.post("/api/reset")
def reset() -> dict[str, Any]:
    cases = reset_queue()
    return {"ok": True, "cases": len(cases)}


if STATIC_DIR.is_dir():
    app.mount("/_next", StaticFiles(directory=STATIC_DIR / "_next"), name="next-static")

    @app.get("/")
    def _index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")
