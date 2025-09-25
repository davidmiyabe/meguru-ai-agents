"""Data schemas for the Meguru application."""

from __future__ import annotations

from datetime import date, datetime, time
import re
from typing import Dict, Iterable, List, Optional, Sequence

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)


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


def _slugify(value: str) -> str:
    """Generate a deterministic, URL-friendly slug."""

    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


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

    @model_validator(mode="before")
    @classmethod
    def _coerce_llm_variants(cls, data: object) -> object:
        """Normalise common deviations produced by the researcher LLM."""

        if not isinstance(data, dict):
            return data

        payload = dict(data)

        def _ensure_list(keys: Iterable[str]) -> None:
            for key in keys:
                if key not in payload:
                    continue
                value = payload[key]
                if isinstance(value, str):
                    parts = [part.strip() for part in re.split(r"[\n,]+", value) if part.strip()]
                    payload[key] = parts
                elif isinstance(value, tuple):
                    payload[key] = list(value)

        _ensure_list(["highlights", "reasons", "why"])
        _ensure_list(["tags", "themes"])

        place_data = payload.get("place") if isinstance(payload.get("place"), dict) else {}
        place_data = dict(place_data) if place_data else {}

        for source_key, target_key in (
            ("name", "name"),
            ("address", "formatted_address"),
            ("formatted_address", "formatted_address"),
        ):
            if source_key in payload and payload[source_key]:
                place_data.setdefault(target_key, payload.pop(source_key))

        if place_data:
            if "address" in place_data and "formatted_address" not in place_data:
                place_data["formatted_address"] = place_data.pop("address")
            payload["place"] = place_data

        place_payload = payload.get("place") if isinstance(payload.get("place"), dict) else None

        if not payload.get("place_id"):
            candidate_id = None
            if isinstance(place_payload, dict):
                candidate_id = place_payload.get("place_id")

            if not candidate_id:
                slug_parts: List[str] = []
                place = place_payload or {}
                if isinstance(place, dict):
                    if place.get("name"):
                        slug_parts.append(str(place["name"]))
                    if place.get("formatted_address"):
                        slug_parts.append(str(place["formatted_address"]))

                summary = payload.get("summary") or payload.get("description")
                if summary and not slug_parts:
                    slug_parts.append(str(summary))

                if not slug_parts and isinstance(payload.get("highlights"), list):
                    highlights = [item for item in payload["highlights"] if isinstance(item, str) and item.strip()]
                    if highlights:
                        slug_parts.append(highlights[0])

                if slug_parts:
                    slug = _slugify(" ".join(slug_parts))
                    if slug:
                        candidate_id = f"generated-{slug}"

            if candidate_id:
                payload["place_id"] = candidate_id
                place_payload = payload.get("place") if isinstance(payload.get("place"), dict) else None
                if isinstance(place_payload, dict) and not place_payload.get("place_id"):
                    place_payload["place_id"] = candidate_id
        elif isinstance(place_payload, dict) and not place_payload.get("place_id"):
            place_payload["place_id"] = payload["place_id"]

        return payload


class ResearchCorpus(BaseModel):
    """Curated set of researched places grouped by theme."""

    @model_validator(mode="before")
    @classmethod
    def _normalise_research_buckets(cls, data: object) -> object:
        """Coerce loose LLM structures into canonical research buckets."""

        if not isinstance(data, dict):
            return data

        payload = dict(data)

        def _normalise_bucket(keys: Sequence[str]) -> None:
            canonical_key = keys[0]
            source_key = None
            for key in keys:
                if key in payload:
                    source_key = key
                    break

            if source_key is None:
                return

            raw_items = payload.get(source_key)

            if raw_items is None:
                normalised_items: List[object] = []
            elif isinstance(raw_items, dict):
                normalised_items = [raw_items]
            elif isinstance(raw_items, (list, tuple, set)):
                normalised_items = list(raw_items)
            else:
                normalised_items = [raw_items]

            cleaned_items: List[object] = []
            for item in normalised_items:
                if isinstance(item, dict):
                    cleaned_items.append(ResearchItem._coerce_llm_variants(item))
                else:
                    cleaned_items.append(item)

            payload[canonical_key] = cleaned_items

            for alias in keys:
                if alias != canonical_key:
                    payload.pop(alias, None)

        _normalise_bucket(("lodgings", "lodging", "stays"))
        _normalise_bucket(("dining", "restaurants", "food"))
        _normalise_bucket(("experiences", "activities", "things_to_do"))

        return payload

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

    @field_validator("date", mode="before")
    @classmethod
    def _coerce_date(cls, value: object) -> Optional[date]:
        """Normalise loose LLM date representations to real dates."""

        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return None
            try:
                return date.fromisoformat(candidate)
            except ValueError:
                return value

        return value


class Itinerary(BaseModel):
    """Structured multi-day trip plan."""

    destination: str = Field(default="")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: List[DayPlan] = Field(default_factory=list)
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _unwrap_common_wrappers(cls, data: object) -> object:
        """Support common nesting variants returned by the LLM."""

        if not isinstance(data, dict):
            return data

        candidate = data
        for key in ("itinerary", "trip"):
            while isinstance(candidate, dict):
                nested = candidate.get(key)
                if not isinstance(nested, dict):
                    break
                candidate = nested

        return candidate

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
