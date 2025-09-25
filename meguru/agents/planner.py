"""Agent that assembles a multi-day itinerary from curated places."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from meguru.agents import DEFAULT_AGENT_MODEL, call_llm_and_validate, format_prompt_data
from meguru.schemas import (
    Itinerary,
    Place,
    ResearchCorpus,
    TasteProfile,
    TripIntent,
    attach_places,
)


class PlannerAgent:
    """Produces a structured itinerary using researched places and traveller tastes."""

    system_prompt = (
        "You are a meticulous travel planner. Create a paced itinerary that respects "
        "opening hours and reasonable travel distances. Provide chronologically ordered "
        "events that include start_time, end_time when possible, duration_minutes, location, "
        "and a brief justification. Use the event category field to denote the slot "
        "(wake_up, breakfast, morning_activity, snack_morning, lunch, afternoon_activity, "
        "snack_afternoon, dinner, evening_activity). Respond with JSON conforming to the "
        "Itinerary schema."
    )
    prompt_version = "planner.v1"

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        stop: Optional[Sequence[str]] = None,
    ) -> None:
        self.model = model or DEFAULT_AGENT_MODEL
        self.stop = stop

    def _build_place_lookup(
        self, corpus: ResearchCorpus, taste: TasteProfile
    ) -> Dict[str, Place]:
        lookup: Dict[str, Place] = {}
        for item in corpus.items():
            if item.place:
                lookup[item.place.place_id] = item.place
        for ranked in taste.items():
            if ranked.place:
                lookup[ranked.place.place_id] = ranked.place
        return lookup

    def run(
        self,
        trip_intent: TripIntent,
        taste_profile: TasteProfile,
        corpus: ResearchCorpus,
    ) -> Itinerary:
        """Return an :class:`Itinerary` based on the traveller preferences."""

        prompt_payload = {
            "trip_intent": trip_intent,
            "taste_profile": taste_profile,
            "research": corpus,
        }

        prompt = (
            "Design a day-by-day itinerary that balances activity pace, observes opening hours, "
            "and minimises unnecessary backtracking.\n"
            "For each day, produce a cohesive theme (store this in the day summary) and a full "
            "schedule covering wake-up, breakfast, morning activity, optional morning snack, "
            "lunch, afternoon activity, optional afternoon snack, dinner, and optional evening "
            "activity.\n"
            "Populate each itinerary event with: category (one of the slots listed above), "
            "start_time in 24-hour HH:MM format, duration_minutes, end_time when known, a "
            "clear title, the location or place_id, and a short justification explaining why "
            "it suits the traveller preferences.\n"
            "If a researched place aligns, reference it by place_id; otherwise include a free-"
            "text location. Keep meal stops distinctive from activities.\n"
            "\n"
            "# Planning Context\n"
            f"{format_prompt_data(prompt_payload)}\n"
            "\n"
            "Output must validate against the Itinerary schema."
        )

        itinerary = call_llm_and_validate(
            schema=Itinerary,
            prompt=prompt,
            system_prompt=self.system_prompt,
            prompt_version=self.prompt_version,
            model=self.model,
            stop=self.stop,
        )

        if not itinerary.destination:
            itinerary.destination = trip_intent.destination

        place_lookup = self._build_place_lookup(corpus, taste_profile)
        attach_places(place_lookup=place_lookup, itinerary=itinerary)

        return itinerary


__all__ = ["PlannerAgent"]
