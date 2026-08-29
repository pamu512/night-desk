from nightdesk.agent import tools
from nightdesk.runtime import current_shift_id
from nightdesk.seed import reset_queue


def test_tools_gather_ring_and_loyalty() -> None:
    reset_queue()
    token = current_shift_id.set("shift-test")
    try:
        opened = tools.list_open_cases()
        assert opened["count"] == 10
        case = tools.get_case("CASE-2401")
        assert case["status"] == "ok"
        graph = tools.get_device_graph("dev_pixel8_aa91")
        assert graph["ring_size"] >= 3
        assert "acc_8f21" in graph["linked_accounts"]
        loyalty = tools.get_loyalty_history("acc_c03a")
        assert loyalty["welcome_bonuses"] == 6
        velocity = tools.get_velocity("CASE-2403")
        assert velocity["auth_fails_15m"] == 14
        travel = tools.get_delivery_and_travel("CASE-2404")
        assert travel["travel"]["itinerary_match"] is True
        note = tools.write_case_note(
            "CASE-2408",
            summary="Benign retry",
            typology="benign_retry",
            evidence=["single PAN"],
            recommended="AUTO_CLOSE",
            confidence=0.88,
        )
        assert note["status"] == "ok"
    finally:
        current_shift_id.reset(token)


def test_unknown_case_is_an_error() -> None:
    reset_queue()
    assert tools.get_case("CASE-NOPE")["status"] == "error"
