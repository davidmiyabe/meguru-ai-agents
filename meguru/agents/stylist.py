"""Stylist agent that polishes curator drafts for the chat surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping

from .curator import CuratorDraft


@dataclass
class StyledResponse:
    """Represents a formatted response ready to stream back to the UI."""

    chunks: List[str] = field(default_factory=list)


class Stylist:
    """Agent that applies tone and rhythm to curator output."""

    system_prompt = (
        "You are Meguru's Stylist. Take the curator's structured notes and deliver a "
        "cinematic yet clear response suited for chat. Keep paragraphs short, lean on "
        "sensory language, and end with momentum."
    )
    prompt_version = "plan.stylist.v1"

    def run(
        self,
        draft: CuratorDraft,
        context: Mapping[str, Any] | Iterable[str] | None = None,
    ) -> StyledResponse:
        """Return a styled response based on a curator draft."""

        mood: str | None = None

        if isinstance(context, Mapping):
            raw_mood = context.get("mood")
            if isinstance(raw_mood, str) and raw_mood.strip():
                mood = raw_mood.strip().lower()

        elif isinstance(context, Iterable) and not isinstance(context, (str, bytes)):
            # Preserve backwards compatibility when only vibes are passed through.
            pass

        body_lines: List[str] = []
        for line in draft.lines:
            cleaned = line.strip()
            if cleaned:
                body_lines.append(cleaned)

        if not body_lines:
            body_lines.append("Still here, still weaving the plan.")

        opener_lookup = {
            "burned_out": "Deep breath—I'm keeping these moves soft and nourishing.",
            "celebration": "Let's pop the confetti—this update is all about the spotlight moments!",
            "peaceful": "Sliding into a serene groove with these next beats.",
        }

        chunks: List[str] = []
        opener = opener_lookup.get(mood or "")
        if opener:
            chunks.append(opener)

        chunks.extend(body_lines)

        if draft.call_to_action:
            cta_lookup = {
                "burned_out": "When you're ready for more ease, just whisper and I'll line up the next calm chapter.",
                "celebration": "Want me to keep the party rolling? Say the word and I'll stack more showstoppers.",
                "peaceful": "If you'd like more tranquil ideas, give me a nod and I'll keep the flow gentle.",
            }
            chunks.append(cta_lookup.get(mood or "", draft.call_to_action))

        return StyledResponse(chunks=chunks)


__all__ = ["Stylist", "StyledResponse"]

