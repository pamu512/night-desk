from pathlib import Path

from nightdesk import config
from nightdesk.facts import facts_from_case
from nightdesk.models import Rails
from nightdesk.policy import decide
from nightdesk.rails import assess_rails
from nightdesk.seed import load_sample_cases


def test_default_config_has_no_project_id(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    assert config.google_cloud_project() == ""
    src = Path(config.__file__).read_text()
    assert "tarka-505801" not in src
    assert 'getenv("GOOGLE_CLOUD_PROJECT", "' not in src


def test_project_string_alone_does_not_mark_vertex_up(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "someone-said-this-is-enough")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    assert config.google_cloud_project() == "someone-said-this-is-enough"
    assert config.has_adc() is False
    assert config.has_gemini() is False
    rails = assess_rails(pubsub_up=True)
    assert rails.ok is False
    assert "vertex" in rails.missing


def test_missing_vertex_or_pubsub_forces_hold() -> None:
    ato = next(c for c in load_sample_cases() if c.id == "CASE-2409")
    facts = facts_from_case(ato)
    vertex_down = Rails(gemini=False, vertex=False, pubsub=True, use_vertex=True)
    got, reason = decide(facts, vertex_down)
    assert got == "HOLD"
    assert "vertex" in reason
    pubsub_down = Rails(gemini=False, vertex=True, pubsub=False, use_vertex=True)
    got, reason = decide(facts, pubsub_down)
    assert got == "HOLD"
    assert "pubsub" in reason
