"""Agent that converts an itinerary into a concise HTML summary."""

from __future__ import annotations

from typing import Optional, Sequence

from meguru.agents import DEFAULT_AGENT_MODEL, call_llm_and_validate, format_prompt_data
from meguru.schemas import Itinerary, ItinerarySummary


class SummaryAgent:
    """Produces a user-friendly HTML overview of an itinerary."""

    system_prompt = (
        "You are a copywriter for a travel service. Summarise the itinerary in an engaging "
        "yet concise way using HTML paragraphs and lists. Respond with JSON containing only an "
        "'html' field."
    )
    prompt_version = "summary.v1"

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        stop: Optional[Sequence[str]] = None,
    ) -> None:
        self.model = model or DEFAULT_AGENT_MODEL
        self.stop = stop

    def run(self, itinerary: Itinerary) -> str:
        """Return an HTML summary for the supplied itinerary."""

        prompt = (
            "Create a short but vivid summary of the itinerary suitable for a trip overview.\n"
            "Use friendly language, highlight each day's focus, and keep the output under 1200 characters.\n"
            "\n"
            "# Itinerary\n"
            f"{format_prompt_data(itinerary)}\n"
            "\n"
            "Respond with JSON containing a single 'html' string."
        )

        summary = call_llm_and_validate(
            schema=ItinerarySummary,
            prompt=prompt,
            system_prompt=self.system_prompt,
            prompt_version=self.prompt_version,
            model=self.model,
            stop=self.stop,
        )

        return summary.html


__all__ = ["SummaryAgent"]
