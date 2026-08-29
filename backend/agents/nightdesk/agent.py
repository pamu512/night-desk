"""ADK package entry (`adk web` / `adk run` from backend/)."""

from nightdesk.agent.adk_agents import load_root_agent

root_agent = load_root_agent()
