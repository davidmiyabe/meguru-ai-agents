from meguru.workflows.plan_chat import PlanConversationWorkflow


def test_selected_card_ids_collects_unique_cards() -> None:
    state = {
        "liked_cards": ["alpha", "beta"],
        "saved_cards": ["beta", "gamma"],
        "liked_inspirations": [{"id": "delta"}],
        "saved_inspirations": [{"id": "gamma"}],
    }

    ids = PlanConversationWorkflow._selected_card_ids(state)
    assert ids == {"alpha", "beta", "gamma", "delta"}


def test_has_prioritised_activity_requires_three_picks() -> None:
    state = {
        "liked_cards": ["one"],
        "saved_cards": [],
        "liked_inspirations": [],
        "saved_inspirations": [],
    }

    assert not PlanConversationWorkflow._has_prioritised_activity(state)

    state["saved_cards"].append("two")
    assert not PlanConversationWorkflow._has_prioritised_activity(state)

    state["liked_inspirations"].append({"id": "three"})
    assert PlanConversationWorkflow._has_prioritised_activity(state)
