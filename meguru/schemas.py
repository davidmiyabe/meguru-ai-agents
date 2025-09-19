"""Data schemas for the Meguru application."""

from __future__ import annotations

from datetime import date, time
from typing import Dict, Iterable, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, PositiveInt


class Place(BaseModel):
    """Normalised representation of a Google Place."""

    place_id: str
    name: str
    formatted_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    types: List[str] = Field(default_factory=list)
    price_level: Optional[int] = None
    business_status: Optional[str] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None
    google_maps_url: Optional[str] = None
    photo_reference: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class Traveler(BaseModel):
    """A person travelling on the trip."""

    name: Optional[str] = None
    age: Optional[PositiveInt] = None
    notes: Optional[str] = None


class TripIntent(BaseModel):
    """Normalised intent gathered from the intake flow."""

    destination: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[PositiveInt] = None
    travelers: List[Traveler] = Field(default_factory=list)
    travel_pace: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("travel_pace", "pace"),
    )
    budget: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    must_do: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    dining_preferences: List[str] = Field(default_factory=list)
    lodging_preferences: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ResearchItem(BaseModel):
    """A researched place annotated for later stages."""

    place_id: str
    place: Optional[Place] = None
    summary: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("summary", "description"),
    )
    highlights: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("highlights", "reasons", "why"),
    )
    suitability: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("suitability", "fit"),
    )
    tags: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("tags", "themes"),
    )


class ResearchCorpus(BaseModel):
    """Curated set of researched places grouped by theme."""

    lodgings: List[ResearchItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("lodgings", "lodging", "stays"),
    )
    dining: List[ResearchItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("dining", "restaurants", "food"),
    )
    experiences: List[ResearchItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("experiences", "activities", "things_to_do"),
    )
    other: List[ResearchItem] = Field(default_factory=list)

    def items(self) -> Iterable[ResearchItem]:
        """Iterate over every research item in the corpus."""

        for bucket in (self.lodgings, self.dining, self.experiences, self.other):
            yield from bucket

    model_config = ConfigDict(populate_by_name=True)


class RankedItem(BaseModel):
    """A scored place surfaced for travellers."""

    place_id: str
    score: float = Field(
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("score", "rating"),
    )
    rationale: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("rationale", "reason"),
    )
    tags: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("tags", "themes"),
    )
    category: Optional[str] = None
    place: Optional[Place] = None


class TasteProfile(BaseModel):
    """Prioritised list of places aligned to a trip intent."""

    top_picks: List[RankedItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("top_picks", "primary", "highlights"),
    )
    backups: List[RankedItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("backups", "secondary", "alternatives"),
    )
    wildcard: List[RankedItem] = Field(
        default_factory=list,
        validation_alias=AliasChoices("wildcard", "wildcards", "extras"),
    )

    def items(self) -> Iterable[RankedItem]:
        for bucket in (self.top_picks, self.backups, self.wildcard):
            yield from bucket

    model_config = ConfigDict(populate_by_name=True)


class ItineraryEvent(BaseModel):
    """An individual scheduled activity inside an itinerary day."""

    title: str
    description: Optional[str] = None
    place_id: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    tags: List[str] = Field(default_factory=list)
    place: Optional[Place] = None


class DayPlan(BaseModel):
    """Plan for a single day of travel."""

    label: Optional[str] = None
    date: Optional[date] = None
    summary: Optional[str] = None
    pace: Optional[str] = None
    events: List[ItineraryEvent] = Field(default_factory=list)


class Itinerary(BaseModel):
    """Structured multi-day trip plan."""

    destination: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: List[DayPlan] = Field(default_factory=list)
    notes: Optional[str] = None

    def all_events(self) -> Iterable[ItineraryEvent]:
        for day in self.days:
            yield from day.events


class ItinerarySummary(BaseModel):
    """Short HTML summary for presenting an itinerary."""

    html: str


class RefinerRequest(BaseModel):
    """Request payload for the itinerary refiner agent."""

    itinerary: Itinerary
    day_index: int = Field(ge=0)
    feedback: str
    additional_constraints: Optional[str] = None


class RefinerResponse(BaseModel):
    """Response returned by the itinerary refiner agent."""

    itinerary: Itinerary
    updated_day: DayPlan
    notes: Optional[str] = None

    def ensure_consistency(self, preferred_index: Optional[int] = None) -> None:
        """Ensure the updated day is placed within the itinerary."""

        if preferred_index is not None:
            while len(self.itinerary.days) <= preferred_index:
                self.itinerary.days.append(DayPlan())
            self.itinerary.days[preferred_index] = self.updated_day
            return

        for idx, day in enumerate(self.itinerary.days):
            if day.date and self.updated_day.date and day.date == self.updated_day.date:
                self.itinerary.days[idx] = self.updated_day
                return
            if day.label and self.updated_day.label and day.label == self.updated_day.label:
                self.itinerary.days[idx] = self.updated_day
                return

        self.itinerary.days.append(self.updated_day)


def attach_places(
    *,
    place_lookup: Dict[str, Place],
    research_items: Iterable[ResearchItem] | None = None,
    ranked_items: Iterable[RankedItem] | None = None,
    itinerary: Itinerary | None = None,
) -> None:
    """Attach :class:`Place` instances to objects that reference a place id."""

    if research_items:
        for item in research_items:
            if isinstance(item.place, dict):
                item.place = Place.model_validate(item.place)
            if item.place is None and item.place_id in place_lookup:
                item.place = place_lookup[item.place_id]

    if ranked_items:
        for item in ranked_items:
            if isinstance(item.place, dict):
                item.place = Place.model_validate(item.place)
            if item.place is None and item.place_id in place_lookup:
                item.place = place_lookup[item.place_id]

    if itinerary:
        for event in itinerary.all_events():
            if isinstance(event.place, dict):
                event.place = Place.model_validate(event.place)
            if event.place is None and event.place_id and event.place_id in place_lookup:
                event.place = place_lookup[event.place_id]


__all__ = [
    "DayPlan",
    "Itinerary",
    "ItineraryEvent",
    "ItinerarySummary",
    "Place",
    "RankedItem",
    "RefinerRequest",
    "RefinerResponse",
    "ResearchCorpus",
    "ResearchItem",
    "TasteProfile",
    "Traveler",
    "TripIntent",
    "attach_places",
]
