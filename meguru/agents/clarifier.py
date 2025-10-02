"""Clarifier agent that crafts follow-up prompts when context is missing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping


@dataclass
class ClarifierPrompt:
    """Structured follow-up produced by the clarifier agent."""

    fields: List[str] = field(default_factory=list)
    message: str = ""

    @property
    def chunks(self) -> List[str]:
        """Return message chunks suitable for streaming in the UI."""

        if not self.message:
            return []
        parts = [segment.strip() for segment in self.message.split("\n") if segment.strip()]
        return parts or [self.message]


class Clarifier:
    """Agent responsible for asking for missing planner context."""

    system_prompt = (
        "You are Meguru's Clarifier. When the Listener flags missing fields, craft a "
        "friendly follow-up question that invites the traveller to share the specifics. "
        "Keep the tone cinematic yet concise and suggest the exact detail needed."
    )
    prompt_version = "plan.clarifier.v1"

    _FIELD_PROMPTS: Dict[str, str] = {
        "destination": "What's the headline city or region you're plotting?",
        "timing": "When should this adventure take place? Share dates or a rough window.",
        "vibe": "Paint the vibe—nightlife, nature, culture? Give me a few keywords.",
        "travel_pace": "Should days feel laid back, balanced, or all-out?",
        "budget": "What budget lane are we in—shoestring, moderate, or splurge?",
        "group": "Who’s coming along and how big is the crew?",
    }

    def run(self, missing_fields: Iterable[str], context: Mapping[str, Any]) -> ClarifierPrompt:
        """Return a clarifying follow-up for the provided fields."""

        fields = [field for field in missing_fields if field in self._FIELD_PROMPTS]
        if not fields:
            return ClarifierPrompt(fields=[], message="Tell me a little more.")

        prompt_lines = [self._FIELD_PROMPTS[fields[0]]]
        if len(fields) > 1:
            extra = ", ".join(self._FIELD_PROMPTS[field] for field in fields[1:])
            prompt_lines.append(extra)

        message = "\n\n".join(prompt_lines)
        return ClarifierPrompt(fields=fields, message=message)


__all__ = ["Clarifier", "ClarifierPrompt"]

