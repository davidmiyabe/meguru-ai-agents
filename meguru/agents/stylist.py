"""Stylist agent that polishes curator drafts for the chat surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

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

    def run(self, draft: CuratorDraft, context: Iterable[str] | None = None) -> StyledResponse:
        """Return a styled response based on a curator draft."""

        chunks: List[str] = []
        for line in draft.lines:
            cleaned = line.strip()
            if cleaned:
                chunks.append(cleaned)

        if draft.call_to_action:
            chunks.append(draft.call_to_action)

        if not chunks:
            chunks.append("Still here, still weaving the plan.")

        return StyledResponse(chunks=chunks)


__all__ = ["Stylist", "StyledResponse"]

