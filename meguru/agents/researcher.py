"""Agent for researching candidate places using Google Maps data."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from meguru.agents import DEFAULT_AGENT_MODEL, call_llm_and_validate, format_prompt_data
from meguru.core import google_api
from meguru.schemas import Place, ResearchCorpus, TripIntent, attach_places


class ResearcherAgent:
    """Curates lodging, dining, and experience options for a trip."""

    system_prompt = (
        "You are a travel researcher. Categorise each place into the correct bucket "
        "and describe why it suits the trip. Only emit JSON that matches the ResearchCorpus schema."
    )
    prompt_version = "researcher.v1"

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        max_results_per_category: int = 5,
    ) -> None:
        self.model = model or DEFAULT_AGENT_MODEL
        self.max_results_per_category = max_results_per_category

    def _build_queries(self, trip_intent: TripIntent) -> Dict[str, List[str]]:
        destination = trip_intent.destination
        interests = trip_intent.interests or []

        lodging_queries = [f"best hotels in {destination}", f"unique stays {destination}"]
        dining_queries = [f"top restaurants {destination}", f"must try food {destination}"]

        experience_queries = [f"things to do {destination}"]
        for interest in interests:
            experience_queries.append(f"{destination} {interest}")

        return {
            "lodgings": lodging_queries,
            "dining": dining_queries,
            "experiences": experience_queries,
        }

    def _gather_places(
        self, queries: Dict[str, List[str]]
    ) -> Dict[str, List[Dict[str, object]]]:
        aggregated: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        seen: set[str] = set()

        for category, category_queries in queries.items():
            for query in category_queries:
                results = google_api.find_places(query)
                for result in results:
                    place_id = result.get("place_id") if isinstance(result, dict) else None
                    if not place_id or place_id in seen:
                        continue

                    seen.add(place_id)
                    details = google_api.place_details(place_id)
                    aggregated[category].append(details)

                    if len(aggregated[category]) >= self.max_results_per_category:
                        break
                if len(aggregated[category]) >= self.max_results_per_category:
                    break

        return aggregated

    def _format_place_details(self, places: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
        formatted: List[Dict[str, object]] = []
        for place in places:
            try:
                formatted.append(Place.model_validate(place).model_dump())
            except Exception:
                # If validation fails we still include the raw payload for the LLM to consider.
                formatted.append(place)
        return formatted

    def run(self, trip_intent: TripIntent) -> ResearchCorpus:
        """Return a :class:`ResearchCorpus` tailored to the provided :class:`TripIntent`."""

        if not trip_intent.destination:
            raise ValueError("Trip intent must include a destination to research.")

        queries = self._build_queries(trip_intent)
        raw_places = self._gather_places(queries)

        prompt_payload = {
            "trip_intent": trip_intent,
            "places": {
                category: self._format_place_details(details)
                for category, details in raw_places.items()
            },
        }

        prompt = (
            "Given the following trip intent and researched Google Places data, "
            "select the most relevant options for lodging, dining, and experiences.\n"
            "Provide concise summaries, highlights, and tags that connect the place to "
            "the traveller's stated interests.\n"
            "\n"
            "# Research Context\n"
            f"{format_prompt_data(prompt_payload)}\n"
            "\n"
            "Respond with JSON adhering to the ResearchCorpus schema."
        )

        corpus = call_llm_and_validate(
            schema=ResearchCorpus,
            prompt=prompt,
            system_prompt=self.system_prompt,
            prompt_version=self.prompt_version,
            model=self.model,
        )

        place_lookup = {
            place_data["place_id"]: Place.model_validate(place_data)
            for category_places in raw_places.values()
            for place_data in category_places
            if isinstance(place_data, dict) and place_data.get("place_id")
        }

        attach_places(place_lookup=place_lookup, research_items=corpus.items())

        return corpus


__all__ = ["ResearcherAgent"]
