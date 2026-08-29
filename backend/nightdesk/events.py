from __future__ import annotations

import asyncio
from collections import defaultdict

from nightdesk.models import TraceEvent, utcnow


class EventBus:
    def __init__(self) -> None:
        self._log: dict[str, list[TraceEvent]] = defaultdict(list)
        self._subs: dict[str, list[asyncio.Queue[TraceEvent | None]]] = defaultdict(list)

    def history(self, shift_id: str) -> list[TraceEvent]:
        return list(self._log[shift_id])

    def emit(
        self,
        shift_id: str,
        *,
        agent: str,
        kind: str,
        message: str,
        case_id: str | None = None,
        data: dict | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            ts=utcnow(),
            shift_id=shift_id,
            case_id=case_id,
            agent=agent,
            kind=kind,  # type: ignore[arg-type]
            message=message,
            data=data or {},
        )
        self._log[shift_id].append(event)
        for q in self._subs[shift_id]:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass
        return event

    def subscribe(self, shift_id: str) -> asyncio.Queue[TraceEvent | None]:
        q: asyncio.Queue[TraceEvent | None] = asyncio.Queue(maxsize=500)
        for ev in self._log[shift_id]:
            q.put_nowait(ev)
        self._subs[shift_id].append(q)
        return q

    def unsubscribe(self, shift_id: str, q: asyncio.Queue[TraceEvent | None]) -> None:
        subs = self._subs.get(shift_id, [])
        if q in subs:
            subs.remove(q)

    def close(self, shift_id: str) -> None:
        for q in list(self._subs[shift_id]):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass


bus = EventBus()
