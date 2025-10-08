"""Trip brief memory agent that persists traveller intent across turns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


def _clean_text(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if value is None:
        return None
    return str(value).strip() or None


def _coerce_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float) and value.is_integer():
        numeric = int(value)
        return numeric if numeric > 0 else None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            numeric = int(cleaned)
        except ValueError:
            return None
        return numeric if numeric > 0 else None
    try:
        numeric = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return numeric if numeric > 0 else None


_OCCASION_KEYWORDS = {
    "anniversary": "anniversary",
    "honeymoon": "honeymoon",
    "birthday": "birthday",
    "proposal": "proposal",
    "babymoon": "babymoon",
}

_MOOD_TONES = {
    "burned_out": "soothing",
    "celebration": "celebratory",
    "peaceful": "calm",
}


@dataclass
class TripBrief:
    """Canonical snapshot of the traveller's intent."""

    destination: Optional[str] = None
    group_type: Optional[str] = None
    group_size: Optional[int] = None
    travel_pace: Optional[str] = None
    budget: Optional[str] = None
    vibes: List[str] = field(default_factory=list)
    mood: Optional[str] = None
    tone: Optional[str] = None
    occasion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "destination": self.destination,
            "group_type": self.group_type,
            "group_size": self.group_size,
            "travel_pace": self.travel_pace,
            "budget": self.budget,
            "vibes": list(self.vibes),
            "mood": self.mood,
            "tone": self.tone,
            "occasion": self.occasion,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TripBrief":
        vibes = []
        raw_vibes = data.get("vibes")
        if isinstance(raw_vibes, Iterable) and not isinstance(raw_vibes, (str, bytes)):
            vibes = [
                str(item).strip()
                for item in raw_vibes
                if isinstance(item, str) and item.strip()
            ]

        return cls(
            destination=_clean_text(data.get("destination")),
            group_type=_clean_text(data.get("group_type")),
            group_size=_coerce_positive_int(data.get("group_size")),
            travel_pace=_clean_text(data.get("travel_pace")),
            budget=_clean_text(data.get("budget")),
            vibes=vibes,
            mood=_clean_text(data.get("mood")),
            tone=_clean_text(data.get("tone")),
            occasion=_clean_text(data.get("occasion")),
        )


class TripBriefMemory:
    """Maintains a persistent trip brief based on listener updates."""

    def __init__(self) -> None:
        self._brief = TripBrief()

    def update(self, state: Mapping[str, Any]) -> TripBrief:
        """Synchronise the memory with the latest planner state."""

        destination = _clean_text(state.get("destination"))
        group_type = _clean_text(state.get("group_type"))
        group_size = _coerce_positive_int(state.get("group_size"))
        travel_pace = _clean_text(state.get("travel_pace"))
        budget = _clean_text(state.get("budget"))
        mood = _clean_text(state.get("mood"))
        tone = _clean_text(state.get("tone"))

        vibes: List[str] = []
        raw_vibes = state.get("vibe")
        if isinstance(raw_vibes, Iterable) and not isinstance(raw_vibes, (str, bytes)):
            seen: Dict[str, None] = {}
            for item in raw_vibes:
                cleaned = _clean_text(item)
                if cleaned and cleaned.lower() not in seen:
                    seen[cleaned.lower()] = None
                    vibes.append(cleaned)

        occasion = _clean_text(state.get("occasion"))
        if not occasion:
            note_text = " ".join(
                str(state.get(key, "")) for key in ("notes", "timing_note") if state.get(key)
            ).lower()
            for keyword, label in _OCCASION_KEYWORDS.items():
                if keyword in note_text:
                    occasion = label
                    break

        if not tone and mood:
            tone = _MOOD_TONES.get(mood.lower())

        brief = TripBrief(
            destination=destination or self._brief.destination,
            group_type=group_type or self._brief.group_type,
            group_size=group_size or self._brief.group_size,
            travel_pace=travel_pace or self._brief.travel_pace,
            budget=budget or self._brief.budget,
            vibes=vibes or list(self._brief.vibes),
            mood=mood or self._brief.mood,
            tone=tone or self._brief.tone,
            occasion=occasion or self._brief.occasion,
        )

        self._brief = brief
        return brief

    @property
    def brief(self) -> TripBrief:
        return self._brief

    def serialise(self) -> Dict[str, Any]:
        return self._brief.to_dict()


__all__ = ["TripBrief", "TripBriefMemory"]

