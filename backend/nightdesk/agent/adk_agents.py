from __future__ import annotations

from nightdesk import config
from nightdesk.agent.tools import INVESTIGATOR_TOOLS

INSTRUCTION = """You are Night Desk. You write the case note. You do not decide money.

You are NOT a chatbot. You do not close cases. A policy guard stamps HOLD or ESCALATE after you write.

For the assigned case, in this order:
1. mark_case_processing(case_id)
2. get_case(case_id)
3. get_account_profile(account_id)
4. get_device_graph(device_id)
5. get_velocity(case_id)
6. get_loyalty_history(account_id)
7. get_delivery_and_travel(case_id)
8. write_case_note(...) once — draft only. recommended must be HOLD or ESCALATE. Never CLOSE.

Rules:
- Never invent evidence. Only cite tool output.
- Never recommend CLOSE or AUTO_CLOSE.
- Do not wait for the user.
"""


def build_root_agent():
    """Google ADK investigator. Imported by `adk web` and the shift runner."""
    from google.adk.agents.llm_agent import Agent

    return Agent(
        model=config.GEMINI_MODEL,
        name="nightdesk_shift_boss",
        description=(
            "Autonomous night-shift agent that triages refund, loyalty, "
            "and payment-abuse cases and writes case notes."
        ),
        instruction=INSTRUCTION,
        tools=INVESTIGATOR_TOOLS,
    )


# ADK CLI (`adk web` / `adk run`) looks for root_agent in this module's parent.
root_agent = None


def load_root_agent():
    global root_agent
    if root_agent is None:
        root_agent = build_root_agent()
    return root_agent
