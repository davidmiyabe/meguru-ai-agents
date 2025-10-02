"""Unit tests for listener and clarifier group handling."""

from __future__ import annotations

from meguru.agents.clarifier import Clarifier
from meguru.agents.listener import Listener
from meguru.workflows.plan_chat import PlanConversationWorkflow


def _base_context() -> dict[str, object]:
    return {
        "destination": "Tokyo",
        "timing_note": "June",
        "vibe": ["Nightlife"],
        "travel_pace": "Balanced",
        "budget": "Moderate",
    }


def test_listener_marks_group_required() -> None:
    listener = Listener()
    assert "group" in listener._required_fields  # type: ignore[attr-defined]


def test_listener_has_field_with_group_signals() -> None:
    listener = Listener()

    assert listener._has_field({"group_type": "Friends trip"}, "group")
    assert listener._has_field({"group_size": "4"}, "group")
    assert not listener._has_field({"group_size": "0"}, "group")
    assert not listener._has_field({}, "group")


def test_detect_missing_group_field() -> None:
    listener = Listener()
    context = _base_context()

    missing = listener._detect_missing_fields(context, [], [])
    assert missing == ["group"]

    context["group_type"] = "Friends trip"
    assert listener._detect_missing_fields(context, [], []) == []


def test_clarifier_prompts_for_group_details() -> None:
    clarifier = Clarifier()
    prompt = clarifier.run(["group"], {})
    assert prompt.fields == ["group"]
    assert "Who’s coming along" in prompt.message


def test_ready_for_gallery_requires_group_signal() -> None:
    state: dict[str, object] = _base_context()
    state["conversation"] = {"pending_fields": []}
    assert not PlanConversationWorkflow.ready_for_gallery(state)

    state["group_size"] = 3
    assert PlanConversationWorkflow.ready_for_gallery(state)
