from meguru.agents.curator import Curator
from meguru.agents.listener import ListenerResult
from meguru.agents.memory import TripBriefMemory


def test_trip_brief_memory_persists_core_fields() -> None:
    memory = TripBriefMemory()
    state = {
        "destination": "Kyoto",
        "group_type": "Partner getaway",
        "group_size": 2,
        "travel_pace": "Laid back",
        "budget": "Moderate",
        "notes": "We're celebrating our anniversary with slow mornings.",
        "vibe": ["Foodie adventures"],
    }

    brief = memory.update(state)
    assert brief.destination == "Kyoto"
    assert brief.group_type == "Partner getaway"
    assert brief.occasion == "anniversary"

    state["mood"] = "celebration"
    state["vibe"].append("Nightlife")

    updated = memory.update(state)
    assert updated.destination == "Kyoto"
    assert updated.tone == "celebratory"
    assert set(updated.vibes) == {"Foodie adventures", "Nightlife"}


def test_curator_references_trip_brief_summary() -> None:
    curator = Curator()
    listener_result = ListenerResult(
        action_type="message",
        user_message="",
        context_updates={},
        missing_context=[],
        resolved_fields=[],
        trigger_planning=False,
    )
    context = {
        "destination": "Kyoto",
        "trip_brief": {
            "destination": "Kyoto",
            "vibes": ["Foodie adventures"],
            "travel_pace": "Laid back",
            "budget": "Moderate",
            "group_type": "Partner getaway",
        },
    }

    draft = curator.run(listener_result, context)
    combined = " ".join(draft.lines).lower()
    assert "kyoto" in combined
    assert "laid back" in combined or "budget" in combined
