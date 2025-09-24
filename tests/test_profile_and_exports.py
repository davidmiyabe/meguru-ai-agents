from datetime import date, time

from meguru.core.exporters import itinerary_to_ics, itinerary_to_pdf
from meguru.core.profile_store import InMemoryProfileStore
from meguru.schemas import DayPlan, Itinerary, ItineraryEvent, Place, TripIntent


def _sample_trip() -> tuple[TripIntent, Itinerary]:
    intent = TripIntent(destination="Kyoto", interests=["Food"])
    itinerary = Itinerary(
        destination="Kyoto",
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 3),
        days=[
            DayPlan(
                label="Day 1",
                events=[
                    ItineraryEvent(
                        title="Visit Fushimi Inari",
                        description="Walk through the torii gates.",
                        start_time=time(9, 0),
                        end_time=time(11, 0),
                        place=Place(
                            place_id="place_123",
                            name="Fushimi Inari Shrine",
                            formatted_address="68 Fukakusa Yabunouchicho, Kyoto",
                        ),
                    )
                ],
            )
        ],
    )
    return intent, itinerary


def test_itinerary_accepts_wrapped_payloads():
    itinerary = Itinerary.model_validate(
        {
            "itinerary": {
                "trip": {
                    "destination": "Tokyo",
                    "days": [
                        {
                            "label": "Day 1",
                            "events": [
                                {
                                    "title": "Tsukiji Outer Market breakfast",
                                    "start_time": "08:30",
                                    "end_time": "10:00",
                                }
                            ],
                        }
                    ],
                }
            }
        }
    )

    assert itinerary.destination == "Tokyo"
    assert itinerary.days[0].events[0].title.startswith("Tsukiji")


def test_itinerary_to_ics_contains_events():
    _, itinerary = _sample_trip()
    ics_data = itinerary_to_ics(itinerary, calendar_name="Kyoto Adventure")
    assert "BEGIN:VEVENT" in ics_data
    assert "Fushimi Inari Shrine" in ics_data


def test_itinerary_to_pdf_starts_with_pdf_header():
    _, itinerary = _sample_trip()
    pdf_bytes = itinerary_to_pdf(itinerary)
    assert pdf_bytes.startswith(b"%PDF-1.4")


def test_in_memory_store_save_and_duplicate():
    intent, itinerary = _sample_trip()
    store = InMemoryProfileStore(user_id="user-1")
    saved = store.save_trip(intent, itinerary)
    assert saved.id in {trip.id for trip in store.list_trips()}
    duplicate = store.duplicate_trip(saved.id)
    assert duplicate is not None
    trip_ids = {trip.id for trip in store.list_trips()}
    assert saved.id in trip_ids and duplicate.id in trip_ids
