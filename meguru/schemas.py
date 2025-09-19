"""Data schemas for the Meguru application."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = ["Place"]
