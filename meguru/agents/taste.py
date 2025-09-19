"""Agent that scores researched places to build a taste profile."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from meguru.agents import DEFAULT_AGENT_MODEL, call_llm_and_validate, format_prompt_data
from meguru.schemas import Place, ResearchCorpus, TasteProfile, TripIntent, attach_places


class TasteAgent:
    """Turns researched places into prioritised recommendations."""

    system_prompt = (
        "You are a seasoned travel curator. Score the researched places and explain why "
        "they align with the traveller's interests. Respond with JSON that matches the "
        "TasteProfile schema."
    )
    prompt_version = "taste.v1"

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        stop: Optional[Sequence[str]] = None,
    ) -> None:
        self.model = model or DEFAULT_AGENT_MODEL
        self.stop = stop

    def _build_place_lookup(self, corpus: ResearchCorpus) -> Dict[str, Place]:
        lookup: Dict[str, Place] = {}
        for item in corpus.items():
            if item.place:
                lookup[item.place.place_id] = item.place
        return lookup

    def run(self, trip_intent: TripIntent, corpus: ResearchCorpus) -> TasteProfile:
        """Return a :class:`TasteProfile` aligned with the :class:`TripIntent`."""

        prompt_payload = {
            "trip_intent": trip_intent,
            "research": corpus,
        }

        prompt = (
            "Given the trip intent and researched options, rank the places.\n"
            "Provide scores between 0 and 1, articulate rationales, and ensure the tags "
            "map back to the traveller's stated interests or constraints.\n"
            "\n"
            "# Context\n"
            f"{format_prompt_data(prompt_payload)}\n"
            "\n"
            "Return JSON that validates against the TasteProfile schema."
        )

        profile = call_llm_and_validate(
            schema=TasteProfile,
            prompt=prompt,
            system_prompt=self.system_prompt,
            prompt_version=self.prompt_version,
            model=self.model,
            stop=self.stop,
        )

        place_lookup = self._build_place_lookup(corpus)
        attach_places(place_lookup=place_lookup, ranked_items=profile.items())

        return profile


__all__ = ["TasteAgent"]
