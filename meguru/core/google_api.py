"""Thin wrapper around the Google Maps/Places HTTP APIs."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests

from meguru.core import db
from meguru.schemas import Place

_GOOGLE_MAPS_BASE_URL = "https://maps.googleapis.com/maps/api"
_DEFAULT_TIMEOUT = float(os.getenv("GOOGLE_MAPS_TIMEOUT", "10"))


class GoogleMapsError(RuntimeError):
    """Raised when the Google Maps API returns an unexpected response."""


def _api_key() -> str:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable is not set")
    return api_key


def _request(path: str, params: Dict[str, object]) -> Dict[str, object]:
    params = {**params, "key": _api_key()}
    response = requests.get(
        f"{_GOOGLE_MAPS_BASE_URL.rstrip('/')}/{path.lstrip('/')}",
        params=params,
        timeout=_DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    status = data.get("status")
    if status and status not in {"OK", "ZERO_RESULTS"}:
        message = data.get("error_message") or status
        raise GoogleMapsError(f"Google Maps API error: {message}")
    return data


def find_places(query: str, location_bias: Optional[tuple[float, float]] = None) -> List[Dict[str, object]]:
    """Search for places using a free text query."""

    params: Dict[str, object] = {"query": query}
    if location_bias:
        params["location"] = f"{location_bias[0]},{location_bias[1]}"
        params["radius"] = os.getenv("GOOGLE_MAPS_SEARCH_RADIUS", "2000")
    data = _request("place/textsearch/json", params)
    return data.get("results", [])  # type: ignore[return-value]


def _normalise_place(result: Dict[str, object], place_id: str) -> Dict[str, object]:
    geometry = result.get("geometry") or {}
    location = geometry.get("location") or {}
    photos = result.get("photos") or []
    photo_reference: Optional[str] = None
    if isinstance(photos, list) and photos:
        first_photo = photos[0] or {}
        if isinstance(first_photo, dict):
            photo_reference = first_photo.get("photo_reference")  # type: ignore[assignment]

    raw_types = result.get("types") or []
    normalised_types: List[str]
    if isinstance(raw_types, list):
        normalised_types = [str(item) for item in raw_types]
    elif raw_types:
        normalised_types = [str(raw_types)]
    else:
        normalised_types = []

    place = Place(
        place_id=result.get("place_id") or place_id,
        name=result.get("name") or "",
        formatted_address=result.get("formatted_address") or result.get("vicinity"),
        latitude=location.get("lat") if isinstance(location, dict) else None,
        longitude=location.get("lng") if isinstance(location, dict) else None,
        rating=result.get("rating"),
        user_ratings_total=result.get("user_ratings_total"),
        types=normalised_types,
        price_level=result.get("price_level"),
        business_status=result.get("business_status"),
        website=result.get("website"),
        phone_number=(
            result.get("formatted_phone_number") or result.get("international_phone_number")
        ),
        google_maps_url=result.get("url"),
        photo_reference=photo_reference,
    )
    return place.model_dump()


def _place_ttl_hours() -> float:
    ttl_env = os.getenv("PLACE_TTL_HOURS")
    if not ttl_env:
        return 24.0
    try:
        return float(ttl_env)
    except ValueError:
        return 24.0


def place_details(place_id: str) -> Dict[str, object]:
    """Return the normalised details for a Google Place, using a database cache."""

    connection = db.get_connection()
    try:
        db.ensure_cache_table(connection)
        cached = db.get_cache_entry(connection, place_id)
        ttl = timedelta(hours=_place_ttl_hours())
        if cached:
            cached_value, updated_at = cached
            if not isinstance(updated_at, datetime):
                raise GoogleMapsError("Invalid cache entry: updated_at is not a datetime")
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - updated_at <= ttl:
                return cached_value

        details_fields = [
            "place_id",
            "name",
            "formatted_address",
            "geometry/location",
            "rating",
            "user_ratings_total",
            "types",
            "price_level",
            "business_status",
            "website",
            "formatted_phone_number",
            "international_phone_number",
            "url",
            "photos",
        ]
        data = _request(
            "place/details/json",
            {"place_id": place_id, "fields": ",".join(details_fields)},
        )
        result = data.get("result")
        if not isinstance(result, dict):
            raise GoogleMapsError("Place details response did not contain a result")
        normalised = _normalise_place(result, place_id)
        db.set_cache_entry(connection, place_id, normalised)
        return normalised
    finally:
        connection.close()


def distance_matrix(
    origins: List[Tuple[float, float]],
    destinations: List[Tuple[float, float]],
    mode: str = "walking",
) -> Dict[str, object]:
    """Call the Google Distance Matrix API."""

    origin_param = "|".join(f"{lat},{lng}" for lat, lng in origins)
    destination_param = "|".join(f"{lat},{lng}" for lat, lng in destinations)
    params = {
        "origins": origin_param,
        "destinations": destination_param,
        "mode": mode,
    }
    return _request("distancematrix/json", params)


__all__ = [
    "GoogleMapsError",
    "distance_matrix",
    "find_places",
    "place_details",
]
