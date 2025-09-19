"""Offline-friendly substitutes for Google Maps API responses."""

from __future__ import annotations

import copy
from math import asin, cos, radians, sin, sqrt
from typing import Dict, Iterable, List, Optional, Tuple

from meguru.schemas import Place


def _place(
    *,
    place_id: str,
    name: str,
    address: str,
    latitude: float,
    longitude: float,
    types: Iterable[str],
    rating: float,
    reviews: int,
    price_level: int,
    website: str,
    phone: str,
    maps_url: str,
) -> Dict[str, object]:
    return Place(
        place_id=place_id,
        name=name,
        formatted_address=address,
        latitude=latitude,
        longitude=longitude,
        rating=rating,
        user_ratings_total=reviews,
        types=list(types),
        price_level=price_level,
        business_status="OPERATIONAL",
        website=website,
        phone_number=phone,
        google_maps_url=maps_url,
        photo_reference=f"stub-photo-{place_id}",
    ).model_dump()


_PLACES: Dict[str, Dict[str, object]] = {
    "kyoto-ryokan-hikari": _place(
        place_id="kyoto-ryokan-hikari",
        name="Ryokan Hikari",
        address="123 Lantern Street, Kyoto",
        latitude=35.0116,
        longitude=135.7681,
        types=["lodging", "spa", "point_of_interest", "establishment"],
        rating=4.8,
        reviews=215,
        price_level=4,
        website="https://example.com/ryokan-hikari",
        phone="+81 75-123-4567",
        maps_url="https://maps.google.com/?cid=kyoto-ryokan-hikari",
    ),
    "kyoto-townhouse-inn": _place(
        place_id="kyoto-townhouse-inn",
        name="Townhouse Inn Gion",
        address="8-1 Hanamikoji Dori, Kyoto",
        latitude=35.0039,
        longitude=135.7722,
        types=["lodging", "point_of_interest", "establishment"],
        rating=4.6,
        reviews=142,
        price_level=3,
        website="https://example.com/townhouse-inn",
        phone="+81 75-765-4321",
        maps_url="https://maps.google.com/?cid=kyoto-townhouse-inn",
    ),
    "kyoto-breakfast-cafe": _place(
        place_id="kyoto-breakfast-cafe",
        name="Kamo Riverside Cafe",
        address="45 Kiyamachi Dori, Kyoto",
        latitude=35.009,
        longitude=135.77,
        types=["cafe", "restaurant", "food", "point_of_interest", "establishment"],
        rating=4.5,
        reviews=320,
        price_level=2,
        website="https://example.com/kamo-cafe",
        phone="+81 75-246-8100",
        maps_url="https://maps.google.com/?cid=kyoto-breakfast-cafe",
    ),
    "kyoto-izakaya-night": _place(
        place_id="kyoto-izakaya-night",
        name="Gion Lantern Izakaya",
        address="12 Yasaka Dori, Kyoto",
        latitude=35.0047,
        longitude=135.7786,
        types=["restaurant", "bar", "food", "point_of_interest", "establishment"],
        rating=4.7,
        reviews=198,
        price_level=3,
        website="https://example.com/gion-lantern",
        phone="+81 75-315-9000",
        maps_url="https://maps.google.com/?cid=kyoto-izakaya-night",
    ),
    "kyoto-kaiseki": _place(
        place_id="kyoto-kaiseki",
        name="Kaiseki Hanakago",
        address="88 Pontocho Alley, Kyoto",
        latitude=35.0082,
        longitude=135.7698,
        types=["restaurant", "food", "point_of_interest", "establishment"],
        rating=4.9,
        reviews=85,
        price_level=4,
        website="https://example.com/kaiseki-hanakago",
        phone="+81 75-600-2255",
        maps_url="https://maps.google.com/?cid=kyoto-kaiseki",
    ),
    "kyoto-bamboo-forest": _place(
        place_id="kyoto-bamboo-forest",
        name="Arashiyama Bamboo Grove",
        address="Sagaogurayama Tabuchiyamacho, Kyoto",
        latitude=35.0094,
        longitude=135.6675,
        types=["tourist_attraction", "park", "point_of_interest", "establishment"],
        rating=4.7,
        reviews=5230,
        price_level=0,
        website="https://example.com/arashiyama-grove",
        phone="+81 75-123-9876",
        maps_url="https://maps.google.com/?cid=kyoto-bamboo-forest",
    ),
    "kyoto-tea-ceremony": _place(
        place_id="kyoto-tea-ceremony",
        name="Tea Ceremony Shoin",
        address="3-2-1 Higashiyama, Kyoto",
        latitude=35.0021,
        longitude=135.7804,
        types=["tourist_attraction", "museum", "point_of_interest", "establishment"],
        rating=4.8,
        reviews=450,
        price_level=2,
        website="https://example.com/tea-ceremony",
        phone="+81 75-789-1234",
        maps_url="https://maps.google.com/?cid=kyoto-tea-ceremony",
    ),
    "kyoto-nishiki-market": _place(
        place_id="kyoto-nishiki-market",
        name="Nishiki Market Food Walk",
        address="609 Nishidaimonjicho, Kyoto",
        latitude=35.0054,
        longitude=135.7661,
        types=["tourist_attraction", "market", "point_of_interest", "establishment"],
        rating=4.6,
        reviews=10450,
        price_level=1,
        website="https://example.com/nishiki-market",
        phone="+81 75-111-2233",
        maps_url="https://maps.google.com/?cid=kyoto-nishiki-market",
    ),
    "kyoto-philosophers-walk": _place(
        place_id="kyoto-philosophers-walk",
        name="Philosopher's Path",
        address="Sakyo Ward, Kyoto",
        latitude=35.0266,
        longitude=135.7982,
        types=["tourist_attraction", "park", "point_of_interest", "establishment"],
        rating=4.5,
        reviews=2890,
        price_level=0,
        website="https://example.com/philosophers-path",
        phone="+81 75-456-7890",
        maps_url="https://maps.google.com/?cid=kyoto-philosophers-walk",
    ),
}


_CATEGORY_INDEX = {
    "lodgings": ["kyoto-ryokan-hikari", "kyoto-townhouse-inn"],
    "dining": ["kyoto-breakfast-cafe", "kyoto-izakaya-night", "kyoto-kaiseki"],
    "experiences": [
        "kyoto-bamboo-forest",
        "kyoto-tea-ceremony",
        "kyoto-nishiki-market",
        "kyoto-philosophers-walk",
    ],
}


def _matching_category(query: str) -> List[str]:
    lowered = query.lower()
    if any(keyword in lowered for keyword in ("hotel", "stay", "lodging", "ryokan")):
        return _CATEGORY_INDEX["lodgings"]
    if any(keyword in lowered for keyword in ("restaurant", "food", "dining", "cafe", "izakaya", "dinner", "breakfast")):
        return _CATEGORY_INDEX["dining"]
    return _CATEGORY_INDEX["experiences"]


def find_places(query: str, location_bias: Optional[tuple[float, float]] = None) -> List[Dict[str, object]]:
    """Return deterministic place search results for offline usage."""

    results: List[Dict[str, object]] = []
    for place_id in _matching_category(query):
        place = _PLACES[place_id]
        geometry = {
            "location": {
                "lat": place.get("latitude"),
                "lng": place.get("longitude"),
            }
        }
        results.append(
            {
                "place_id": place_id,
                "name": place.get("name"),
                "formatted_address": place.get("formatted_address"),
                "types": place.get("types", []),
                "geometry": geometry,
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "photos": [{"photo_reference": place.get("photo_reference")}],
            }
        )
    return results


def place_details(place_id: str) -> Dict[str, object]:
    """Return cached place details for the provided ``place_id``."""

    place = _PLACES.get(place_id)
    if not place:
        raise KeyError(f"Unknown stub place_id: {place_id}")
    return copy.deepcopy(place)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius_km * c


_SPEED_KMH = {
    "walking": 5.0,
    "bicycling": 15.0,
    "driving": 35.0,
}


def _travel_time_minutes(distance_km: float, mode: str) -> int:
    speed = _SPEED_KMH.get(mode, _SPEED_KMH["walking"])
    if speed <= 0:
        speed = _SPEED_KMH["walking"]
    return max(1, int((distance_km / speed) * 60))


def distance_matrix(
    origins: List[Tuple[float, float]],
    destinations: List[Tuple[float, float]],
    mode: str = "walking",
) -> Dict[str, object]:
    """Return a simplified distance matrix between origin/destination points."""

    rows: List[Dict[str, object]] = []
    for origin in origins:
        origin_lat, origin_lng = origin
        elements: List[Dict[str, object]] = []
        for destination in destinations:
            dest_lat, dest_lng = destination
            km = _haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
            minutes = _travel_time_minutes(km, mode)
            elements.append(
                {
                    "status": "OK",
                    "distance": {"text": f"{km:.1f} km", "value": int(km * 1000)},
                    "duration": {"text": f"{minutes} mins", "value": minutes * 60},
                }
            )
        rows.append({"elements": elements})

    return {"status": "OK", "rows": rows}


def request(path: str, params: Dict[str, object]) -> Dict[str, object]:
    """Emulate the JSON payload returned by specific Google API endpoints."""

    if "textsearch" in path:
        query = str(params.get("query", ""))
        return {"status": "OK", "results": find_places(query)}
    if "details" in path:
        place_id = str(params.get("place_id"))
        return {"status": "OK", "result": place_details(place_id)}
    if "distancematrix" in path:
        origins_raw = str(params.get("origins", ""))
        destinations_raw = str(params.get("destinations", ""))
        origins = [
            tuple(float(value) for value in item.split(","))
            for item in origins_raw.split("|")
            if item
        ]
        destinations = [
            tuple(float(value) for value in item.split(","))
            for item in destinations_raw.split("|")
            if item
        ]
        return distance_matrix(origins, destinations, str(params.get("mode", "walking")))
    raise KeyError(f"Unsupported stub endpoint: {path}")


__all__ = ["distance_matrix", "find_places", "place_details", "request"]

