"""Agent that refines an itinerary based on user feedback."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from meguru.agents import DEFAULT_AGENT_MODEL, call_llm_and_validate, format_prompt_data
from meguru.schemas import Itinerary, Place, RefinerRequest, RefinerResponse, attach_places


class RefinerAgent:
    """Adjusts a specific itinerary day in response to traveller feedback."""

    system_prompt = (
        "You refine travel plans. Update the specified day to address the traveller's feedback "
        "while keeping the overall itinerary coherent. Only return JSON that conforms to the "
        "RefinerResponse schema."
    )
    prompt_version = "refiner.v1"

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        stop: Optional[Sequence[str]] = None,
    ) -> None:
        self.model = model or DEFAULT_AGENT_MODEL
        self.stop = stop

    def _build_place_lookup(self, *itineraries: Itinerary) -> Dict[str, Place]:
        lookup: Dict[str, Place] = {}
        for itinerary in itineraries:
            for event in itinerary.all_events():
                if event.place:
                    lookup[event.place.place_id] = event.place
        return lookup

    def run(
        self,
        request: RefinerRequest,
        *,
        additional_places: Optional[Dict[str, Place]] = None,
    ) -> RefinerResponse:
        """Return a :class:`RefinerResponse` honouring the provided feedback."""

        prompt_payload = {
            "request": request,
        }

        prompt = (
            "Using the supplied feedback, adjust only the specified day of the itinerary.\n"
            "Maintain logical pacing, avoid duplicate activities across the trip, and respect "
            "any constraints.\n"
            "\n"
            "# Refinement Context\n"
            f"{format_prompt_data(prompt_payload)}\n"
            "\n"
            "Return JSON validating against the RefinerResponse schema."
        )

        response = call_llm_and_validate(
            schema=RefinerResponse,
            prompt=prompt,
            system_prompt=self.system_prompt,
            prompt_version=self.prompt_version,
            model=self.model,
            stop=self.stop,
        )

        response.ensure_consistency(preferred_index=request.day_index)

        lookup = self._build_place_lookup(request.itinerary, response.itinerary)
        if additional_places:
            lookup.update(additional_places)

        attach_places(place_lookup=lookup, itinerary=response.itinerary)

        return response


__all__ = ["RefinerAgent"]
