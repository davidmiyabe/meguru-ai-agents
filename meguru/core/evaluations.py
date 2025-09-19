"""Lightweight quality checks for generated itineraries."""

from __future__ import annotations

from datetime import time
from math import asin, cos, radians, sin, sqrt
from typing import Mapping, MutableMapping, Sequence

from meguru.schemas import Itinerary, ItineraryEvent


_MEAL_TAGS = {"meal", "breakfast", "lunch", "dinner", "brunch", "supper"}


def _event_coordinates(event: ItineraryEvent) -> tuple[float, float] | None:
    place = event.place
    if (
        place is None
        or place.latitude is None
        or place.longitude is None
    ):
        return None
    return (place.latitude, place.longitude)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the spherical distance in kilometres between two coordinates."""

    radius_km = 6371.0

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius_km * c


def daily_transfer_distance_km(itinerary: Itinerary) -> Mapping[str, float]:
    """Calculate per-day transfer distances using event coordinates."""

    totals: MutableMapping[str, float] = {}
    for index, day in enumerate(itinerary.days):
        prev_coords: tuple[float, float] | None = None
        total_distance = 0.0
        for event in day.events:
            coords = _event_coordinates(event)
            if prev_coords and coords:
                total_distance += _haversine_km(*prev_coords, *coords)
            if coords:
                prev_coords = coords
        label = day.label or f"Day {index + 1}"
        totals[label] = total_distance
    return totals


def _has_valid_times(event: ItineraryEvent) -> bool:
    return event.start_time is not None and event.end_time is not None


def _times_overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def opening_hours_conflicts(itinerary: Itinerary) -> int:
    """Return the count of events whose times conflict within each day."""

    conflicts = 0
    for day in itinerary.days:
        timed_events = [event for event in day.events if _has_valid_times(event)]
        timed_events.sort(key=lambda event: event.start_time)
        for event in timed_events:
            if event.start_time and event.end_time and event.end_time <= event.start_time:
                conflicts += 1
        for first, second in zip(timed_events, timed_events[1:]):
            if (
                first.start_time
                and first.end_time
                and second.start_time
                and second.end_time
                and _times_overlap(first.start_time, first.end_time, second.start_time, second.end_time)
            ):
                conflicts += 1
    return conflicts


def category_diversity_score(itinerary: Itinerary) -> int:
    """Return the count of distinct activity categories across the itinerary."""

    categories: set[str] = set()
    for event in itinerary.all_events():
        categories.update(
            tag.lower()
            for tag in event.tags
            if tag and tag.lower() not in _MEAL_TAGS
        )
        place = event.place
        if place and place.types:
            categories.update(t.lower() for t in place.types if t)
    return len(categories)


def has_meal_coverage(itinerary: Itinerary, *, required_tags: Sequence[str] | None = None) -> bool:
    """Return True when each day contains at least one meal-tagged event."""

    if not itinerary.days:
        return False

    required = {tag.lower() for tag in required_tags} if required_tags else _MEAL_TAGS

    for day in itinerary.days:
        if not day.events:
            return False

        meal_found = False
        for event in day.events:
            tags = {tag.lower() for tag in event.tags}
            title = event.title.lower()
            if tags & required:
                meal_found = True
                break
            if any(token in title for token in required):
                meal_found = True
                break
        if not meal_found:
            return False
    return True


__all__ = [
    "daily_transfer_distance_km",
    "opening_hours_conflicts",
    "category_diversity_score",
    "has_meal_coverage",
]
