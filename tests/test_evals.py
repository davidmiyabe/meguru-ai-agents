from __future__ import annotations

from datetime import date, time

from meguru.core.evaluations import (
    category_diversity_score,
    daily_transfer_distance_km,
    has_meal_coverage,
    opening_hours_conflicts,
)
from meguru.schemas import DayPlan, Itinerary, ItineraryEvent, Place


def _place(place_id: str, name: str, latitude: float, longitude: float, *, types: list[str]) -> Place:
    return Place(
        place_id=place_id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        types=types,
    )


def _build_sample_itinerary() -> Itinerary:
    morning_cafe = _place(
        "cafe-kyoto",
        "Morning Cafe",
        35.0116,
        135.7681,
        types=["restaurant", "cafe", "food"],
    )
    bamboo_grove = _place(
        "bamboo-grove",
        "Bamboo Grove Walk",
        35.0150,
        135.7697,
        types=["tourist_attraction", "park"],
    )
    tea_house = _place(
        "tea-house",
        "Tea Ceremony House",
        35.0120,
        135.7650,
        types=["point_of_interest", "museum"],
    )
    downtown_izakaya = _place(
        "izakaya",
        "Downtown Izakaya",
        35.0105,
        135.7705,
        types=["restaurant", "bar", "food"],
    )

    riverside_cafe = _place(
        "riverside-cafe",
        "Riverside Breakfast",
        35.0090,
        135.7700,
        types=["restaurant", "cafe", "food"],
    )
    art_museum = _place(
        "art-museum",
        "Kyoto Art Museum",
        35.0140,
        135.7800,
        types=["museum", "point_of_interest"],
    )
    zen_garden = _place(
        "zen-garden",
        "Zen Garden",
        35.0180,
        135.7760,
        types=["park", "tourist_attraction"],
    )
    kaiseki_dinner = _place(
        "kaiseki",
        "Kaiseki Dinner",
        35.0115,
        135.7690,
        types=["restaurant", "food"],
    )

    return Itinerary(
        destination="Kyoto",
        start_date=date(2024, 6, 1),
        end_date=date(2024, 6, 3),
        days=[
            DayPlan(
                label="Day 1",
                events=[
                    ItineraryEvent(
                        title="Breakfast at Morning Cafe",
                        start_time=time(8, 0),
                        end_time=time(9, 0),
                        place=morning_cafe,
                        tags=["meal", "breakfast"],
                    ),
                    ItineraryEvent(
                        title="Walk through the Bamboo Grove",
                        start_time=time(9, 30),
                        end_time=time(11, 0),
                        place=bamboo_grove,
                        tags=["nature"],
                    ),
                    ItineraryEvent(
                        title="Traditional Tea Ceremony",
                        start_time=time(13, 0),
                        end_time=time(15, 0),
                        place=tea_house,
                        tags=["culture"],
                    ),
                    ItineraryEvent(
                        title="Dinner at local izakaya",
                        start_time=time(18, 30),
                        end_time=time(20, 0),
                        place=downtown_izakaya,
                        tags=["meal", "dinner"],
                    ),
                ],
            ),
            DayPlan(
                label="Day 2",
                events=[
                    ItineraryEvent(
                        title="Riverside breakfast",
                        start_time=time(8, 30),
                        end_time=time(9, 30),
                        place=riverside_cafe,
                        tags=["meal", "breakfast"],
                    ),
                    ItineraryEvent(
                        title="Explore Kyoto Art Museum",
                        start_time=time(10, 0),
                        end_time=time(12, 30),
                        place=art_museum,
                        tags=["art"],
                    ),
                    ItineraryEvent(
                        title="Stroll the Zen Garden",
                        start_time=time(14, 0),
                        end_time=time(16, 0),
                        place=zen_garden,
                        tags=["relaxation"],
                    ),
                    ItineraryEvent(
                        title="Evening kaiseki dinner",
                        start_time=time(18, 0),
                        end_time=time(20, 0),
                        place=kaiseki_dinner,
                        tags=["meal", "dinner"],
                    ),
                ],
            ),
        ],
    )


def test_daily_distance_sanity() -> None:
    itinerary = _build_sample_itinerary()
    distances = daily_transfer_distance_km(itinerary)

    assert distances, "Expected daily distance data to be calculated"
    assert all(total < 15 for total in distances.values())


def test_opening_hours_conflicts_zero() -> None:
    itinerary = _build_sample_itinerary()
    assert opening_hours_conflicts(itinerary) == 0


def test_category_diversity_threshold() -> None:
    itinerary = _build_sample_itinerary()
    assert category_diversity_score(itinerary) >= 4


def test_meal_coverage_present_each_day() -> None:
    itinerary = _build_sample_itinerary()
    assert has_meal_coverage(itinerary)
