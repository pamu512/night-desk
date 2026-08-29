from nightdesk.facts import facts_from_case
from nightdesk.models import CaseNote, CaseRecord, Rails
from nightdesk.policy import CLOSED, decide, fired_evidence, stamp_note
from nightdesk.seed import load_sample_cases

# Facts-only (rails up): slam-dunks escalate; nobody closes.
EXPECTED_UP = {
    "CASE-2401": "ESCALATE",
    "CASE-2402": "ESCALATE",
    "CASE-2403": "ESCALATE",
    "CASE-2404": "HOLD",
    "CASE-2405": "HOLD",
    "CASE-2406": "ESCALATE",
    "CASE-2407": "ESCALATE",
    "CASE-2408": "HOLD",
    "CASE-2409": "ESCALATE",
    "CASE-2410": "HOLD",
}

RAILS_UP = Rails(gemini=True, vertex=True, pubsub=True, use_vertex=False)
RAILS_DOWN = Rails(gemini=False, vertex=False, pubsub=False, use_vertex=False)


def test_decide_cannot_close() -> None:
    cases = load_sample_cases()
    for case in cases:
        got, _ = decide(facts_from_case(case), RAILS_UP)
        assert got not in CLOSED
        assert got in {"HOLD", "ESCALATE"}
        got_down, reason = decide(facts_from_case(case), RAILS_DOWN)
        assert got_down == "HOLD"
        assert "Fail-closed" in reason


def test_decide_is_two_way_when_rails_up() -> None:
    cases = {c.id: c for c in load_sample_cases()}
    for case_id, want in EXPECTED_UP.items():
        got, reason = decide(facts_from_case(cases[case_id]), RAILS_UP)
        assert got == want, f"{case_id}: got {got} ({reason}), want {want}"


def test_fail_closed_hold_when_gemini_down() -> None:
    ato = next(c for c in load_sample_cases() if c.id == "CASE-2409")
    rails = Rails(gemini=False, vertex=False, pubsub=True, use_vertex=False)
    got, reason = decide(facts_from_case(ato), rails)
    assert got == "HOLD"
    assert "gemini" in reason


def test_fail_closed_hold_when_vertex_down() -> None:
    ato = next(c for c in load_sample_cases() if c.id == "CASE-2409")
    rails = Rails(gemini=False, vertex=False, pubsub=True, use_vertex=True)
    got, reason = decide(facts_from_case(ato), rails)
    assert got == "HOLD"
    assert "vertex" in reason


def test_fail_closed_hold_when_pubsub_down() -> None:
    ring = next(c for c in load_sample_cases() if c.id == "CASE-2401")
    rails = Rails(gemini=True, vertex=True, pubsub=False, use_vertex=False)
    got, reason = decide(facts_from_case(ring), rails)
    assert got == "HOLD"
    assert "pubsub" in reason


def test_traveler_is_hold_not_close() -> None:
    case = next(c for c in load_sample_cases() if c.id == "CASE-2404")
    got, _ = decide(facts_from_case(case), RAILS_UP)
    assert got == "HOLD"


def test_note_stamp_uses_decide_not_narrative() -> None:
    case = next(c for c in load_sample_cases() if c.id == "CASE-2401")
    facts = facts_from_case(case)
    draft = CaseNote(
        summary=case.narrative,
        typology=case.typology,
        evidence=["a story about lockers"],
        recommended="HOLD",
        why_human="model waffle",
    )
    stamped = stamp_note(case, facts, RAILS_UP, gemini_draft=draft)
    assert stamped.note is not None
    final, reason = decide(facts, RAILS_UP)
    assert stamped.note.summary == f"{final}: {reason}"
    assert stamped.note.recommended == final
    assert stamped.note.why_human == reason
    assert stamped.note.evidence == fired_evidence(facts)
    assert case.narrative not in stamped.note.summary
    assert "lockers" not in " ".join(stamped.note.evidence)
    assert "device_ring" in " ".join(stamped.note.evidence)
    assert stamped.note.override is True
    assert stamped.note.gemini_recommended == "HOLD"
    assert stamped.policy_override is True


def test_fired_evidence_only_named_signals() -> None:
    case = next(c for c in load_sample_cases() if c.id == "CASE-2409")
    ev = fired_evidence(facts_from_case(case))
    blob = " ".join(ev)
    assert "ATO" in blob
    assert "device_ring" not in blob
    assert "narrative" not in blob.lower()
