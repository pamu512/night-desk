from nightdesk.facts import facts_from_case
from nightdesk.models import CaseRecord
from nightdesk.policy import apply_confidence, decide
from nightdesk.seed import load_sample_cases

EXPECTED = {
    "CASE-2401": "AUTO_ESCALATE",
    "CASE-2402": "AUTO_ESCALATE",
    "CASE-2403": "AUTO_ESCALATE",
    "CASE-2404": "AUTO_CLOSE",
    "CASE-2405": "HUMAN_QUEUE",
    "CASE-2406": "AUTO_ESCALATE",
    "CASE-2407": "AUTO_ESCALATE",
    "CASE-2408": "AUTO_CLOSE",
    "CASE-2409": "AUTO_ESCALATE",
    "CASE-2410": "HUMAN_QUEUE",
}


def test_sample_cases_match_labeled_guesses() -> None:
    cases = {c.id: c for c in load_sample_cases()}
    assert set(cases) == set(EXPECTED)
    for case_id, want in EXPECTED.items():
        got, reason = decide(facts_from_case(cases[case_id]))
        assert got == want, f"{case_id}: got {got} ({reason}), want {want}"


def test_low_confidence_is_forced_to_human() -> None:
    final, reason, over = apply_confidence("AUTO_CLOSE", 0.4, "looks fine")
    assert final == "HUMAN_QUEUE"
    assert over is True
    assert "0.40" in reason


def test_confident_escalate_passes() -> None:
    final, _reason, over = apply_confidence("AUTO_ESCALATE", 0.9, "ato")
    assert final == "AUTO_ESCALATE"
    assert over is False


def test_ato_beats_tenure() -> None:
    case = CaseRecord(
        id="CASE-X",
        typology="account_takeover",
        title="t",
        amount_usd=20,
        alerted_at="2026-08-29T00:00:00Z",
        narrative="n",
        account={"age_days": 4000, "prior_fraud_cases": 0, "chargebacks_90d": 0},
        ato={"password_reset": True},
    )
    got, _ = decide(facts_from_case(case))
    assert got == "AUTO_ESCALATE"
