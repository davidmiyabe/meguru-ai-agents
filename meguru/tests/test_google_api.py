from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from meguru.core import db, google_api
from meguru.schemas import Place


class FakeCursor:
    def __init__(self, rows: List[Dict[str, Any]], actions: List[Any]):
        self._rows = rows
        self._actions = actions
        self._last_query = ""

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D401 - signature required by context manager protocol
        return None

    def execute(self, query: str, params: Any = None) -> None:
        self._last_query = query
        self._actions.append(("execute", query, params))

    def fetchone(self) -> Dict[str, Any] | None:
        if self._rows:
            return self._rows.pop(0)
        return None


class FakeConnection:
    def __init__(self, rows: List[Dict[str, Any]] | None = None):
        self.rows = list(rows or [])
        self.actions: List[Any] = []
        self.closed = False

    def cursor(self, *args: Any, **kwargs: Any) -> FakeCursor:
        return FakeCursor(self.rows, self.actions)

    def commit(self) -> None:
        self.actions.append("commit")

    def close(self) -> None:
        self.closed = True


def _new_place(name: str) -> Dict[str, Any]:
    return Place(
        place_id="place_123",
        name=name,
        formatted_address="123 Example Street",
        latitude=1.23,
        longitude=4.56,
        rating=4.7,
        user_ratings_total=100,
        types=["restaurant"],
        price_level=2,
        business_status="OPERATIONAL",
        website="https://example.com",
        phone_number="123",
        google_maps_url="https://maps.google.com/?cid=123",
    ).model_dump()


def test_place_details_returns_cached_value_when_not_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    cached_place = _new_place("Cached")
    fake_conn = FakeConnection(
        rows=[{"value": cached_place, "updated_at": datetime.now(timezone.utc)}]
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "key")
    monkeypatch.setenv("PLACE_TTL_HOURS", "24")
    monkeypatch.setattr(db, "get_connection", lambda: fake_conn)
    monkeypatch.setattr(google_api, "_request", lambda *args, **kwargs: pytest.fail("API should not be called"))

    result = google_api.place_details("place_123")

    assert result == cached_place
    assert fake_conn.closed is True


def test_place_details_calls_api_when_cache_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_conn = FakeConnection(rows=[])
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "key")
    monkeypatch.setenv("PLACE_TTL_HOURS", "24")
    monkeypatch.setattr(db, "get_connection", lambda: fake_conn)

    new_payload = {
        "status": "OK",
        "result": {
            "place_id": "place_123",
            "name": "Fresh Place",
            "formatted_address": "456 New Street",
            "geometry": {"location": {"lat": 9.87, "lng": 6.54}},
            "rating": 4.9,
            "user_ratings_total": 10,
            "types": ["cafe"],
            "price_level": 3,
            "business_status": "OPERATIONAL",
            "website": "https://fresh.example.com",
            "formatted_phone_number": "+1 555-0100",
            "url": "https://maps.google.com/?cid=456",
        },
    }

    recorded_cache: Dict[str, Any] = {}

    def fake_set_cache(connection: FakeConnection, key: str, value: Dict[str, Any]) -> None:
        recorded_cache["key"] = key
        recorded_cache["value"] = value

    monkeypatch.setattr(db, "set_cache_entry", fake_set_cache)
    monkeypatch.setattr(google_api, "_request", lambda *args, **kwargs: new_payload)

    result = google_api.place_details("place_123")

    expected = Place(
        place_id="place_123",
        name="Fresh Place",
        formatted_address="456 New Street",
        latitude=9.87,
        longitude=6.54,
        rating=4.9,
        user_ratings_total=10,
        types=["cafe"],
        price_level=3,
        business_status="OPERATIONAL",
        website="https://fresh.example.com",
        phone_number="+1 555-0100",
        google_maps_url="https://maps.google.com/?cid=456",
        photo_reference=None,
    ).model_dump()

    assert result == expected
    assert recorded_cache["key"] == "place_123"
    assert recorded_cache["value"] == expected
    assert fake_conn.closed is True


def test_place_details_refreshes_cache_when_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    cached_place = _new_place("Old")
    fake_conn = FakeConnection(
        rows=[
            {
                "value": cached_place,
                "updated_at": datetime.now(timezone.utc) - timedelta(hours=48),
            }
        ]
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "key")
    monkeypatch.setenv("PLACE_TTL_HOURS", "1")
    monkeypatch.setattr(db, "get_connection", lambda: fake_conn)

    new_payload = {
        "status": "OK",
        "result": {
            "place_id": "place_123",
            "name": "Updated Place",
            "formatted_address": "456 New Street",
            "geometry": {"location": {"lat": 2.0, "lng": 3.0}},
            "rating": 4.5,
            "user_ratings_total": 25,
            "types": ["museum"],
            "price_level": 1,
            "business_status": "OPERATIONAL",
            "website": "https://updated.example.com",
            "international_phone_number": "+81 90-0000-0000",
            "url": "https://maps.google.com/?cid=789",
        },
    }

    recorded_cache: Dict[str, Any] = {}

    def fake_set_cache(connection: FakeConnection, key: str, value: Dict[str, Any]) -> None:
        recorded_cache["key"] = key
        recorded_cache["value"] = value

    monkeypatch.setattr(db, "set_cache_entry", fake_set_cache)
    monkeypatch.setattr(google_api, "_request", lambda *args, **kwargs: new_payload)

    result = google_api.place_details("place_123")

    expected = Place(
        place_id="place_123",
        name="Updated Place",
        formatted_address="456 New Street",
        latitude=2.0,
        longitude=3.0,
        rating=4.5,
        user_ratings_total=25,
        types=["museum"],
        price_level=1,
        business_status="OPERATIONAL",
        website="https://updated.example.com",
        phone_number="+81 90-0000-0000",
        google_maps_url="https://maps.google.com/?cid=789",
        photo_reference=None,
    ).model_dump()

    assert result == expected
    assert recorded_cache["key"] == "place_123"
    assert recorded_cache["value"] == expected
    assert fake_conn.closed is True
