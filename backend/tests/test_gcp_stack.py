def test_adk_and_gcp_clients_import() -> None:
    from google.adk.agents.llm_agent import Agent
    from google.cloud import firestore
    from google.cloud import pubsub_v1

    assert Agent is not None
    assert firestore.Client is not None
    assert pubsub_v1.PublisherClient is not None


def test_root_agent_builds_without_calling_gemini() -> None:
    from nightdesk.agent.adk_agents import build_root_agent

    agent = build_root_agent()
    assert agent.name == "nightdesk_shift_boss"
    assert agent.tools
