from meguru.ui.plan import _prepare_activity_cards


def _base_state() -> dict:
    return {
        "destination": "Kyoto",
        "vibe": ["Outdoors & nature"],
        "travel_pace": "Laid back",
        "budget": "Shoestring",
        "group_type": "Partner getaway",
        "mood": "peaceful",
        "trip_brief": {
            "destination": "Kyoto",
            "vibes": ["Outdoors & nature"],
            "travel_pace": "Laid back",
            "budget": "Shoestring",
            "group_type": "Partner getaway",
            "mood": "peaceful",
            "tone": "calm",
        },
        "custom_interests": [],
        "liked_cards": [],
        "saved_cards": [],
        "liked_inspirations": [],
        "saved_inspirations": [],
        "_activity_catalog": {},
    }


def test_prepare_activity_cards_prioritises_brief_matches() -> None:
    state = _base_state()
    cards, _, _ = _prepare_activity_cards(state)
    assert cards
    # Gallery is capped to top matches
    assert len(cards) <= 4
    assert cards[0]["id"] == "forest_baths"


def test_prepare_activity_cards_retains_liked_cards() -> None:
    state = _base_state()
    state["liked_cards"] = ["neon_bazaar"]
    state["trip_brief"]["vibes"].append("Nightlife")

    cards, likes, _ = _prepare_activity_cards(state)
    ids = [card["id"] for card in cards]

    assert "neon_bazaar" in ids
    # Forced cards still count toward the target length
    assert len(cards) >= len(likes)
