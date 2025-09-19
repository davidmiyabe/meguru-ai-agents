"""Persistence helpers for storing trips and itineraries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

from meguru.core.supabase_api import SupabaseClient, SupabaseError, SupabaseSession
from meguru.schemas import Itinerary, ItineraryEvent, Place, TripIntent


@dataclass(slots=True)
class StoredTrip:
    """Trip persisted in a backing store."""

    id: str
    user_id: str
    name: str
    destination: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    intent: TripIntent
    itinerary: Itinerary


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.split("T")[0])
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            cleaned = value.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None
    return None


def _event_slot(event: ItineraryEvent, fallback_index: int) -> Optional[str]:
    slot_windows = (
        ("Morning", time(6, 0), time(11, 0)),
        ("Lunch", time(11, 0), time(14, 0)),
        ("Afternoon", time(14, 0), time(17, 0)),
        ("Dinner", time(17, 0), time(20, 30)),
        ("Evening", time(20, 30), time(23, 59, 59)),
    )
    slot_keywords = {
        "breakfast": "Morning",
        "brunch": "Morning",
        "coffee": "Morning",
        "sunrise": "Morning",
        "lunch": "Lunch",
        "midday": "Lunch",
        "afternoon": "Afternoon",
        "tea": "Afternoon",
        "museum": "Afternoon",
        "dinner": "Dinner",
        "supper": "Dinner",
        "tasting": "Dinner",
        "evening": "Evening",
        "night": "Evening",
        "drinks": "Evening",
        "bar": "Evening",
        "show": "Evening",
    }

    if event.start_time:
        for name, start, end in slot_windows:
            if start <= event.start_time <= end:
                return name

    haystack_parts = [
        event.title or "",
        event.description or "",
        " ".join(event.tags or []),
    ]
    if event.place and event.place.name:
        haystack_parts.append(event.place.name)
    haystack = " ".join(part.lower() for part in haystack_parts if part)
    for keyword, slot_name in slot_keywords.items():
        if keyword in haystack:
            return slot_name
    slots = ["Morning", "Lunch", "Afternoon", "Dinner", "Evening"]
    return slots[fallback_index % len(slots)] if slots else None


class InMemoryProfileStore:
    """Fallback store used when Supabase is not configured."""

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._records: MutableMapping[str, StoredTrip] = {}

    def _next_id(self) -> str:
        return str(uuid.uuid4())

    def save_trip(self, intent: TripIntent, itinerary: Itinerary, *, name: Optional[str] = None) -> StoredTrip:
        trip_id = self._next_id()
        now = datetime.now(timezone.utc)
        record = StoredTrip(
            id=trip_id,
            user_id=self._user_id,
            name=name or itinerary.destination or intent.destination or "Trip",
            destination=itinerary.destination,
            start_date=itinerary.start_date,
            end_date=itinerary.end_date,
            created_at=now,
            updated_at=now,
            intent=intent,
            itinerary=itinerary,
        )
        self._records[trip_id] = record
        return record

    def list_trips(self) -> List[StoredTrip]:
        return sorted(
            self._records.values(),
            key=lambda trip: trip.created_at or datetime.now(timezone.utc),
            reverse=True,
        )

    def get_trip(self, trip_id: str) -> Optional[StoredTrip]:
        return self._records.get(trip_id)

    def duplicate_trip(self, trip_id: str) -> Optional[StoredTrip]:
        original = self._records.get(trip_id)
        if not original:
            return None
        copy = StoredTrip(
            id=self._next_id(),
            user_id=self._user_id,
            name=f"{original.name} (Copy)",
            destination=original.destination,
            start_date=original.start_date,
            end_date=original.end_date,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            intent=original.intent.model_copy(deep=True),
            itinerary=original.itinerary.model_copy(deep=True),
        )
        self._records[copy.id] = copy
        return copy


class SupabaseProfileStore:
    """Supabase-backed implementation of trip persistence."""

    def __init__(self, client: SupabaseClient, session: SupabaseSession) -> None:
        self._client = client
        self._session = session

    @property
    def user_id(self) -> str:
        return self._session.user.id

    def _ensure_user(self) -> None:
        user = self._session.user
        payload = {
            "id": user.id,
            "email": user.email,
            "full_name": user.raw.get("user_metadata", {}).get("full_name") if isinstance(user.raw, Mapping) else None,
            "avatar_url": user.raw.get("user_metadata", {}).get("avatar_url") if isinstance(user.raw, Mapping) else None,
        }
        self._client.insert(
            "users",
            [payload],
            access_token=self._session.access_token,
            returning=False,
            prefer_resolution="merge-duplicates",
            on_conflict="id",
        )

    def _build_place_rows(self, itinerary_id: str, itinerary: Itinerary) -> List[Mapping[str, Any]]:
        seen: Dict[str, Place] = {}
        rows: List[Mapping[str, Any]] = []
        for day in itinerary.days:
            for event in day.events:
                if not event.place:
                    continue
                place = event.place
                place_key = place.place_id or f"{place.name}-{place.formatted_address}" if place.name else None
                if not place_key:
                    continue
                if place_key in seen:
                    continue
                seen[place_key] = place
                rows.append(
                    {
                        "itinerary_id": itinerary_id,
                        "place_id": place.place_id,
                        "name": place.name,
                        "data": place.model_dump(mode="json"),
                    }
                )
        return rows

    def _build_event_rows(self, itinerary_id: str, itinerary: Itinerary) -> List[Mapping[str, Any]]:
        rows: List[Mapping[str, Any]] = []
        for day_index, day in enumerate(itinerary.days):
            event_date = day.date
            for event_index, event in enumerate(day.events):
                start_dt = None
                end_dt = None
                if event_date and event.start_time:
                    start_dt = datetime.combine(event_date, event.start_time)
                if event_date and event.end_time:
                    end_dt = datetime.combine(event_date, event.end_time)
                slot = _event_slot(event, event_index)
                rows.append(
                    {
                        "itinerary_id": itinerary_id,
                        "day_index": day_index,
                        "event_index": event_index,
                        "starts_at": start_dt.isoformat() if start_dt else None,
                        "ends_at": end_dt.isoformat() if end_dt else None,
                        "slot": slot,
                        "data": event.model_dump(mode="json"),
                    }
                )
        return rows

    def _compose_trip(self, trip_row: Mapping[str, Any], itinerary_row: Optional[Mapping[str, Any]]) -> StoredTrip:
        intent_payload = trip_row.get("trip_intent") or {}
        intent = TripIntent.model_validate(intent_payload)
        itinerary_payload: Dict[str, Any] = {}
        if itinerary_row:
            itinerary_payload = itinerary_row.get("itinerary") or {}
            if itinerary_row.get("notes") and "notes" not in itinerary_payload:
                itinerary_payload["notes"] = itinerary_row.get("notes")
        itinerary = Itinerary.model_validate(itinerary_payload) if itinerary_payload else Itinerary(
            destination=intent.destination or trip_row.get("destination") or intent.notes or "Trip"
        )
        start_date = _parse_date(trip_row.get("start_date"))
        end_date = _parse_date(trip_row.get("end_date"))
        created_at = _parse_datetime(trip_row.get("created_at"))
        updated_at = _parse_datetime(trip_row.get("updated_at"))
        return StoredTrip(
            id=str(trip_row.get("id")),
            user_id=str(trip_row.get("user_id")),
            name=str(trip_row.get("name") or itinerary.destination or intent.destination or "Trip"),
            destination=trip_row.get("destination") or itinerary.destination,
            start_date=start_date or itinerary.start_date,
            end_date=end_date or itinerary.end_date,
            created_at=created_at,
            updated_at=updated_at,
            intent=intent,
            itinerary=itinerary,
        )

    def _fetch_trip_rows(self, *, trip_id: Optional[str] = None) -> List[StoredTrip]:
        filters: Dict[str, Any] = {"user_id": f"eq.{self.user_id}"}
        if trip_id:
            filters["id"] = f"eq.{trip_id}"
        rows = self._client.select(
            "trips",
            access_token=self._session.access_token,
            filters=filters,
            select="*,itineraries(*)",
            order="updated_at.desc",
        )
        records: List[StoredTrip] = []
        for row in rows:
            itineraries = row.get("itineraries") or []
            itinerary_row = itineraries[0] if itineraries else None
            try:
                records.append(self._compose_trip(row, itinerary_row))
            except Exception as exc:  # noqa: BLE001 - surface data errors to callers
                raise SupabaseError(f"Failed to parse trip payload: {exc}") from exc
        return records

    def list_trips(self) -> List[StoredTrip]:
        return self._fetch_trip_rows()

    def get_trip(self, trip_id: str) -> Optional[StoredTrip]:
        rows = self._fetch_trip_rows(trip_id=trip_id)
        return rows[0] if rows else None

    def save_trip(self, intent: TripIntent, itinerary: Itinerary, *, name: Optional[str] = None) -> StoredTrip:
        self._ensure_user()
        trip_name = name or itinerary.destination or intent.destination or "Trip"
        trip_payload = {
            "user_id": self.user_id,
            "name": trip_name,
            "destination": itinerary.destination,
            "start_date": itinerary.start_date.isoformat() if itinerary.start_date else None,
            "end_date": itinerary.end_date.isoformat() if itinerary.end_date else None,
            "trip_intent": intent.model_dump(mode="json"),
        }
        trip_rows = self._client.insert("trips", [trip_payload], access_token=self._session.access_token)
        if not trip_rows:
            raise SupabaseError("Supabase did not return trip row on insert")
        trip_row = trip_rows[0]
        trip_id = str(trip_row.get("id"))
        itinerary_payload = {
            "trip_id": trip_id,
            "itinerary": itinerary.model_dump(mode="json"),
            "notes": itinerary.notes,
        }
        itinerary_rows = self._client.insert("itineraries", [itinerary_payload], access_token=self._session.access_token)
        itinerary_row = itinerary_rows[0] if itinerary_rows else None
        itinerary_id = str(itinerary_row.get("id")) if itinerary_row else None
        if itinerary_id:
            place_rows = self._build_place_rows(itinerary_id, itinerary)
            if place_rows:
                self._client.insert(
                    "places",
                    place_rows,
                    access_token=self._session.access_token,
                    returning=False,
                )
            event_rows = self._build_event_rows(itinerary_id, itinerary)
            if event_rows:
                self._client.insert(
                    "events",
                    event_rows,
                    access_token=self._session.access_token,
                    returning=False,
                )
        stored = self.get_trip(trip_id)
        if not stored:
            raise SupabaseError("Unable to fetch stored trip after insert")
        return stored

    def duplicate_trip(self, trip_id: str) -> Optional[StoredTrip]:
        original = self.get_trip(trip_id)
        if not original:
            return None
        return self.save_trip(
            original.intent.model_copy(deep=True),
            original.itinerary.model_copy(deep=True),
            name=f"{original.name} (Copy)",
        )


__all__ = [
    "InMemoryProfileStore",
    "StoredTrip",
    "SupabaseProfileStore",
]

