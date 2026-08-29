from __future__ import annotations

import logging

from nightdesk import config
from nightdesk.agent.adk_agents import build_root_agent
from nightdesk.events import bus
from nightdesk.models import CaseRecord
from nightdesk.store import store

log = logging.getLogger("nightdesk.gemini")


async def investigate_case_gemini(case_id: str, shift_id: str) -> CaseRecord:
    """Run the ADK + Gemini 3.5 investigator for a single case."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    case = store.get_case(case_id)
    if not case:
        raise RuntimeError(f"unknown case {case_id}")

    agent = build_root_agent()
    session_service = InMemorySessionService()
    app_name = "nightdesk"
    user_id = "night-shift"
    session_id = f"{shift_id}-{case_id}"
    await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

    prompt = (
        f"Investigate case {case_id} only. Title: {case.title}. "
        f"Amount ${case.amount_usd:.2f}. Typology {case.typology}. "
        "Claim it, gather context with tools, write one case note, then stop. "
        "Do not touch other cases."
    )
    bus.emit(
        shift_id,
        agent="shift_boss",
        kind="plan",
        case_id=case_id,
        message=f"Gemini {config.GEMINI_MODEL} investigating {case_id}",
    )
    content = types.Content(role="user", parts=[types.Part(text=prompt)])
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        text = ""
        if getattr(event, "content", None) and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts if getattr(p, "text", None))
        if text:
            bus.emit(
                shift_id,
                agent="shift_boss",
                kind="info",
                case_id=case_id,
                message=text[:400],
            )
        fn = getattr(event, "get_function_calls", None)
        if callable(fn):
            for call in fn() or []:
                bus.emit(
                    shift_id,
                    agent="shift_boss",
                    kind="tool",
                    case_id=case_id,
                    message=f"Gemini called {call.name}",
                    data={"args": getattr(call, "args", {}) or {}},
                )

    refreshed = store.get_case(case_id)
    if refreshed is None:
        raise RuntimeError(f"case vanished: {case_id}")
    # If the model skipped the note, the mock note builder is not used —
    # the shift runner will fall back so the queue still drains.
    return refreshed
