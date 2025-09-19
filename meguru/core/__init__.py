"""Core utilities for Meguru."""

from .evaluations import (
    category_diversity_score,
    daily_transfer_distance_km,
    has_meal_coverage,
    opening_hours_conflicts,
)

__all__ = [
    "category_diversity_score",
    "daily_transfer_distance_km",
    "has_meal_coverage",
    "opening_hours_conflicts",
]
