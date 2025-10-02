"""Curator agent that shapes the planning narrative from listener updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping

from .listener import ListenerResult


@dataclass
class CuratorDraft:
    """Narrative scaffold produced by the curator."""

    lines: List[str] = field(default_factory=list)
    call_to_action: str | None = None


class Curator:
    """Agent that turns structured updates into a conversational draft."""

    system_prompt = (
        "You are Meguru's Curator. Compose warm, cinematic planning responses based on "
        "structured updates from the Listener. Celebrate new details, reinforce what "
        "was captured, and hint at next steps."
    )
    prompt_version = "plan.curator.v1"

    def run(self, listener_result: ListenerResult, context: Mapping[str, Any]) -> CuratorDraft:
        """Return a curator draft responding to the traveller action."""

        destination = str(context.get("destination") or "your trip")
        lines: List[str] = []

        if listener_result.action_type == "message":
            if listener_result.context_updates.get("destination"):
                lines.append(
                    f"{destination} is where the reel lights up—I'll build the next act around that skyline."
                )
            elif listener_result.context_updates.get("vibe_add"):
                vibes = listener_result.context_updates["vibe_add"]
                chips = " ".join(f"`{vibe}`" for vibe in sorted(set(vibes)))
                lines.append(f"Those vibes hit different. I'll weave in {chips} as key motifs.")
            else:
                lines.append(f"Noted for {destination}. I'll keep threading this into the plan.")

            if listener_result.context_updates.get("timing_note"):
                lines.append("Timing locked—I'll map experiences to that window.")
            if listener_result.context_updates.get("travel_pace"):
                pace = listener_result.context_updates["travel_pace"].lower()
                lines.append(f"Setting the pace dial to {pace}.")
            if listener_result.context_updates.get("budget"):
                budget = listener_result.context_updates["budget"].lower()
                lines.append(f"I'll curate with a {budget} lens so every moment feels right.")

        elif listener_result.action_type in {"like_activity", "save_activity"}:
            card = listener_result.context_updates.get("activity_catalog", {})
            card_id = None
            if listener_result.context_updates.get("liked_cards_add"):
                card_id = listener_result.context_updates["liked_cards_add"][0]
            if listener_result.context_updates.get("saved_cards_add"):
                card_id = listener_result.context_updates["saved_cards_add"][0]

            if card_id and isinstance(card, dict):
                details = card.get(card_id, {})
                title = details.get("title") or card_id
                lines.append(f"Adding **{title}** to the storyboard.")
                if details.get("location_hint"):
                    lines.append(details["location_hint"])
            else:
                lines.append("Adding that idea to the inspiration board.")

        elif listener_result.action_type in {"unlike_activity", "unsave_activity"}:
            lines.append("All good—I'll trim that from the set list.")
        else:
            lines.append("Got it. Keeping the momentum going.")

        if not lines:
            lines.append("Noted. I'll keep this shaping the journey.")

        call_to_action = None
        if listener_result.missing_context:
            call_to_action = "Drop those details when you're ready and I'll keep refining."

        return CuratorDraft(lines=lines, call_to_action=call_to_action)


__all__ = ["Curator", "CuratorDraft"]

